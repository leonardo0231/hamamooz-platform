from django.http import FileResponse, Http404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hamamooz.apps.accounts.models import Role
from hamamooz.apps.attendance.models import AttendanceRecord, AttendanceSession
from hamamooz.apps.core.viewsets import AuditedModelViewSet
from hamamooz.apps.guidance.models import GuideActionPlan
from hamamooz.apps.recommendations.models import Recommendation
from hamamooz.apps.reports.models import ReportArchive
from hamamooz.apps.students.models import GuardianAccount, Student, StudentAccount

from .models import PortalVisibilityPolicy
from .serializers import (
    PortalAttendanceSerializer,
    PortalChildrenResponseSerializer,
    PortalGuidePlansResponseSerializer,
    PortalRecommendationsResponseSerializer,
    PortalReportsResponseSerializer,
    PortalVisibilityPolicySerializer,
)

DEFAULT_VISIBILITY = {
    PortalVisibilityPolicy.Resource.REPORT_CARD: PortalVisibilityPolicy.Visibility.RELEASED,
    PortalVisibilityPolicy.Resource.RECOMMENDATIONS: PortalVisibilityPolicy.Visibility.APPROVED_ONLY,
    PortalVisibilityPolicy.Resource.ATTENDANCE_SUMMARY: PortalVisibilityPolicy.Visibility.VISIBLE,
    PortalVisibilityPolicy.Resource.BEHAVIOR: PortalVisibilityPolicy.Visibility.HIDDEN,
    PortalVisibilityPolicy.Resource.COUNSELING: PortalVisibilityPolicy.Visibility.NEVER,
    PortalVisibilityPolicy.Resource.GUIDE_PLAN: PortalVisibilityPolicy.Visibility.RELEASED,
}


def policy_value(organization_id, resource):
    # Counseling stays non-negotiably absent even if a malformed database row exists.
    if resource == PortalVisibilityPolicy.Resource.COUNSELING:
        return PortalVisibilityPolicy.Visibility.NEVER
    policy = PortalVisibilityPolicy.objects.filter(
        organization_id=organization_id, resource=resource
    ).first()
    return policy.visibility if policy else DEFAULT_VISIBILITY[resource]


def guardian_for_request(request):
    account = (
        GuardianAccount.objects.filter(user=request.user, is_active=True)
        .select_related("guardian")
        .first()
    )
    if not account:
        raise PermissionDenied("This account is not an active guardian portal account.")
    return account.guardian


def student_for_request(request):
    account = (
        StudentAccount.objects.filter(user=request.user, is_active=True)
        .select_related("student")
        .first()
    )
    if not account:
        raise PermissionDenied("This account is not an active student portal account.")
    return account.student


def guardian_visible_student(guardian, student_id):
    student = (
        Student.objects.filter(id=student_id, guardian_links__guardian=guardian).distinct().first()
    )
    if not student:
        raise Http404
    return student


def portal_reports(student):
    if (
        policy_value(student.organization_id, PortalVisibilityPolicy.Resource.REPORT_CARD)
        != "released"
    ):
        return ReportArchive.objects.none()
    return ReportArchive.objects.filter(
        enrollment__student=student,
        status=ReportArchive.Status.COMPLETED,
        released_at__isnull=False,
    ).select_related("term")


def portal_recommendations(student, audience):
    if (
        policy_value(student.organization_id, PortalVisibilityPolicy.Resource.RECOMMENDATIONS)
        != "approved_only"
    ):
        return Recommendation.objects.none()
    return Recommendation.objects.filter(
        enrollment__student=student,
        audience=audience,
        status=Recommendation.Status.APPROVED,
    )


def portal_guide_plans(student):
    if (
        policy_value(student.organization_id, PortalVisibilityPolicy.Resource.GUIDE_PLAN)
        != "released"
    ):
        return GuideActionPlan.objects.none()
    return GuideActionPlan.objects.filter(
        assignment__enrollment__student=student,
        visibility=GuideActionPlan.Visibility.RELEASED,
    )


class PortalBaseView(APIView):
    permission_classes = [IsAuthenticated]

    def children_response(self, student):
        return {"id": str(student.id), "full_name": student.full_name, "status": student.status}

    def reports_response(self, student):
        return [
            {
                "id": str(report.id),
                "report_type": report.report_type,
                "output_format": report.output_format,
                "term": report.term.title,
                "created_at": report.created_at,
                "released_at": report.released_at,
            }
            for report in portal_reports(student)
        ]

    def recommendations_response(self, student, audience):
        return [
            {
                "id": str(item.id),
                "priority": item.priority,
                "approved_text": item.approved_text,
                "approved_at": item.approved_at,
            }
            for item in portal_recommendations(student, audience)
        ]

    def attendance_response(self, student):
        if (
            policy_value(
                student.organization_id, PortalVisibilityPolicy.Resource.ATTENDANCE_SUMMARY
            )
            != "visible"
        ):
            return {
                "finalized_session_count": 0,
                "unexcused_absence_count": 0,
                "excused_absence_count": 0,
            }
        records = AttendanceRecord.objects.filter(
            enrollment__student=student, session__status=AttendanceSession.Status.FINALIZED
        )
        return {
            "finalized_session_count": records.values("session_id").distinct().count(),
            "unexcused_absence_count": records.filter(
                status=AttendanceRecord.Status.ABSENT_UNEXCUSED
            ).count(),
            "excused_absence_count": records.filter(
                status=AttendanceRecord.Status.ABSENT_EXCUSED
            ).count(),
        }

    def guide_plans_response(self, student):
        return [
            {
                "id": str(plan.id),
                "title": plan.title,
                "objectives": plan.objectives,
                "released_at": plan.released_at,
            }
            for plan in portal_guide_plans(student)
        ]

    def download_report(self, report):
        if not report.output_file:
            raise Http404
        report.output_file.open("rb")
        extension = "docx" if report.output_format == ReportArchive.OutputFormat.DOCX else "pdf"
        content_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if extension == "docx"
            else "application/pdf"
        )
        return FileResponse(
            report.output_file,
            as_attachment=True,
            filename=f"released-report-{report.id}.{extension}",
            content_type=content_type,
        )


class PortalVisibilityPolicyViewSet(AuditedModelViewSet):
    """Organization-level visibility policy; counseling remains hard-denied in code."""

    queryset = PortalVisibilityPolicy.objects.none()
    serializer_class = PortalVisibilityPolicySerializer
    filterset_fields = ["organization", "resource", "visibility"]
    required_roles_by_action = {
        action: [Role.SYSTEM_ADMIN, Role.ORGANIZATION_ADMIN]
        for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        from hamamooz.apps.accounts.access import accessible_organization_ids

        return PortalVisibilityPolicy.objects.filter(
            organization_id__in=accessible_organization_ids(self.request.user)
        )


class ParentChildrenView(PortalBaseView):
    @extend_schema(responses={200: PortalChildrenResponseSerializer})
    def get(self, request):
        guardian = guardian_for_request(request)
        students = Student.objects.filter(guardian_links__guardian=guardian).distinct()
        return Response({"children": [self.children_response(student) for student in students]})


class ParentChildReportsView(PortalBaseView):
    @extend_schema(responses={200: PortalReportsResponseSerializer})
    def get(self, request, student_id):
        student = guardian_visible_student(guardian_for_request(request), student_id)
        return Response({"reports": self.reports_response(student)})


class ParentChildRecommendationsView(PortalBaseView):
    @extend_schema(responses={200: PortalRecommendationsResponseSerializer})
    def get(self, request, student_id):
        student = guardian_visible_student(guardian_for_request(request), student_id)
        return Response(
            {
                "recommendations": self.recommendations_response(
                    student, Recommendation.Audience.PARENT
                )
            }
        )


class ParentChildAttendanceView(PortalBaseView):
    @extend_schema(responses={200: PortalAttendanceSerializer})
    def get(self, request, student_id):
        student = guardian_visible_student(guardian_for_request(request), student_id)
        return Response(self.attendance_response(student))


class ParentChildGuidePlansView(PortalBaseView):
    @extend_schema(responses={200: PortalGuidePlansResponseSerializer})
    def get(self, request, student_id):
        student = guardian_visible_student(guardian_for_request(request), student_id)
        return Response({"guide_plans": self.guide_plans_response(student)})


class ParentChildReportDownloadView(PortalBaseView):
    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    def get(self, request, student_id, report_id):
        student = guardian_visible_student(guardian_for_request(request), student_id)
        report = portal_reports(student).filter(pk=report_id).first()
        if not report:
            raise Http404
        return self.download_report(report)


class StudentReportsView(PortalBaseView):
    @extend_schema(responses={200: PortalReportsResponseSerializer})
    def get(self, request):
        return Response({"reports": self.reports_response(student_for_request(request))})


class StudentRecommendationsView(PortalBaseView):
    @extend_schema(responses={200: PortalRecommendationsResponseSerializer})
    def get(self, request):
        student = student_for_request(request)
        return Response(
            {
                "recommendations": self.recommendations_response(
                    student, Recommendation.Audience.STUDENT
                )
            }
        )


class StudentAttendanceView(PortalBaseView):
    @extend_schema(responses={200: PortalAttendanceSerializer})
    def get(self, request):
        return Response(self.attendance_response(student_for_request(request)))


class StudentGuidePlansView(PortalBaseView):
    @extend_schema(responses={200: PortalGuidePlansResponseSerializer})
    def get(self, request):
        return Response({"guide_plans": self.guide_plans_response(student_for_request(request))})


class StudentReportDownloadView(PortalBaseView):
    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    def get(self, request, report_id):
        student = student_for_request(request)
        report = portal_reports(student).filter(pk=report_id).first()
        if not report:
            raise Http404
        return self.download_report(report)
