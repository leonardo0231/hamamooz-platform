from collections import defaultdict

from django.db.models import Avg, Count, F, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from hamamooz.apps.academics.models import Assessment, CourseOffering, Score, TermResult
from hamamooz.apps.accounts.access import (
    allowed_class_ids,
    broad_access_school_ids,
    selected_school_ids,
    user_has_role,
)
from hamamooz.apps.accounts.models import Role, RoleAssignment
from hamamooz.apps.analytics.models import OperationalAlert, StudentRiskSignal
from hamamooz.apps.behavior.models import BehaviorEvent
from hamamooz.apps.core.models import AuditEvent
from hamamooz.apps.counseling.models import CounselingCase, Referral
from hamamooz.apps.guidance.models import GuideFollowUp, GuideTeacherAssignment
from hamamooz.apps.organizations.models import ClassSection, Term
from hamamooz.apps.reports.models import ReportDraft
from hamamooz.apps.students.models import Enrollment

from .serializers import DashboardSummarySerializer, RoleDashboardSerializer


class DashboardSummaryView(APIView):
    @extend_schema(responses={200: DashboardSummarySerializer})
    def get(self, request):
        school_ids = selected_school_ids(request)
        term_id = request.query_params.get("term")
        term_queryset = (
            Term.objects.select_related("academic_year")
            .filter(academic_year__organization__schools__id__in=school_ids)
            .distinct()
        )
        if term_id:
            try:
                term = term_queryset.get(pk=term_id)
            except (Term.DoesNotExist, ValueError, TypeError) as exc:
                raise ValidationError({"term": "نوبت انتخاب‌شده معتبر نیست."}) from exc
        else:
            today = timezone.localdate()
            term = (
                term_queryset.filter(starts_on__lte=today, ends_on__gte=today)
                .order_by("starts_on")
                .first()
                or term_queryset.filter(academic_year__is_current=True)
                .order_by("starts_on")
                .first()
            )
            if term is None:
                raise ValidationError({"term": "برای شعبه انتخاب‌شده نوبت فعالی تعریف نشده است."})
        class_ids = allowed_class_ids(request.user, school_ids)
        broad_school_ids = broad_access_school_ids(request.user, school_ids)
        enrollments = Enrollment.objects.filter(
            school_id__in=school_ids,
            class_section_id__in=class_ids,
            status=Enrollment.Status.ACTIVE,
        )
        classes = ClassSection.objects.filter(id__in=class_ids, is_active=True)
        offerings = CourseOffering.objects.filter(
            class_section_id__in=class_ids,
            class_section__school_id__in=school_ids,
            term=term,
            is_active=True,
        ).filter(Q(class_section__school_id__in=broad_school_ids) | Q(teacher=request.user))
        assessments = Assessment.objects.filter(course_offering__in=offerings)

        open_assessments = assessments.filter(
            status__in=[
                Assessment.Status.DRAFT,
                Assessment.Status.SUBMITTED,
                Assessment.Status.REJECTED,
            ]
        ).values("id", "course_offering__class_section_id")
        assessment_rows = list(open_assessments)
        active_by_class = defaultdict(set)
        for class_id, enrollment_id in Enrollment.objects.filter(
            class_section_id__in=class_ids,
            status=Enrollment.Status.ACTIVE,
        ).values_list("class_section_id", "id"):
            active_by_class[class_id].add(enrollment_id)
        entered_by_assessment = defaultdict(set)
        for assessment_id, enrollment_id in (
            Score.objects.filter(assessment_id__in=[row["id"] for row in assessment_rows])
            .exclude(status=Score.Status.NOT_ENTERED)
            .values_list("assessment_id", "enrollment_id")
        ):
            entered_by_assessment[assessment_id].add(enrollment_id)
        missing_scores = sum(
            len(
                active_by_class[row["course_offering__class_section_id"]]
                - entered_by_assessment[row["id"]]
            )
            for row in assessment_rows
        )

        class_averages = list(
            TermResult.objects.filter(
                enrollment__class_section_id__in=class_ids,
                term=term,
                average__isnull=False,
            )
            .values("enrollment__class_section_id", "enrollment__class_section__title")
            .annotate(average=Avg("average"), students=Count("enrollment", distinct=True))
            .order_by("enrollment__class_section__title")
        )
        workflow = {
            item["status"]: item["count"]
            for item in assessments.values("status").annotate(count=Count("id"))
        }
        activities = list(
            AuditEvent.objects.filter(
                Q(school_id__in=broad_school_ids) | Q(school_id__in=school_ids, actor=request.user)
            ).values("id", "action", "entity_type", "entity_id", "actor_id", "created_at")[:10]
        )
        by_school = list(
            enrollments.values(
                school_name=F("school__name"),
                organization_name=F("school__organization__name"),
            )
            .annotate(students=Count("student_id", distinct=True))
            .order_by("organization_name", "school_name")
        )
        return Response(
            {
                "selected_term": {
                    "id": str(term.id),
                    "title": term.title,
                },
                "counts": {
                    "students": enrollments.values("student_id").distinct().count(),
                    "classes": classes.count(),
                    "teachers": offerings.values("teacher_id").distinct().count(),
                    "missing_scores": missing_scores,
                },
                "students_by_school": by_school,
                "class_averages": class_averages,
                "assessment_workflow": workflow,
                "latest_activities": activities,
                "quick_links": {
                    "score_entry": "/api/v1/assessments/",
                    "report_cards": "/api/v1/reports/",
                    "imports": "/api/v1/imports/",
                },
            }
        )


class RoleDashboardView(APIView):
    """Read-only role dashboard base with a scope check at the API boundary."""

    dashboard_name = ""
    accepted_roles: list[str] = []
    strict_direct_role = False

    def scoped_school_ids(self, request):
        selected = selected_school_ids(request)
        if self.strict_direct_role:
            permitted = RoleAssignment.objects.filter(
                user=request.user,
                role__in=self.accepted_roles,
                school_id__in=selected,
                is_active=True,
                is_deleted=False,
            ).values_list("school_id", flat=True)
            school_ids = list(permitted)
        else:
            school_ids = [
                school_id
                for school_id in selected
                if user_has_role(request.user, self.accepted_roles, school_id=school_id)
            ]
        if not school_ids:
            raise PermissionDenied("You do not have access to this dashboard scope.")
        return school_ids

    def metrics(self, request, school_ids):
        raise NotImplementedError

    def drill_down(self):
        return {}

    @extend_schema(responses={200: RoleDashboardSerializer})
    def get(self, request):
        school_ids = self.scoped_school_ids(request)
        response = {
            "dashboard": self.dashboard_name,
            "scope_school_ids": school_ids,
            "metrics": self.metrics(request, school_ids),
            "drill_down": self.drill_down(),
        }
        return Response(RoleDashboardSerializer(response).data)


class ManagerDashboardView(RoleDashboardView):
    dashboard_name = "manager"
    accepted_roles = [Role.ORGANIZATION_ADMIN, Role.SCHOOL_MANAGER]

    def metrics(self, request, school_ids):
        active_signals = StudentRiskSignal.objects.filter(
            school_id__in=school_ids, state=StudentRiskSignal.State.ACTIVE
        )
        return {
            "active_students": Enrollment.objects.filter(
                school_id__in=school_ids, status=Enrollment.Status.ACTIVE
            )
            .values("student_id")
            .distinct()
            .count(),
            "high_risk_signals": active_signals.filter(
                severity__in=[StudentRiskSignal.Severity.HIGH, StudentRiskSignal.Severity.CRITICAL]
            ).count(),
            "open_operational_alerts": OperationalAlert.objects.filter(
                signal__school_id__in=school_ids, status=OperationalAlert.Status.OPEN
            ).count(),
            "submitted_report_drafts": ReportDraft.objects.filter(
                school_id__in=school_ids, status=ReportDraft.Status.SUBMITTED
            ).count(),
        }

    def drill_down(self):
        return {
            "alerts": "/api/v1/analytics/operational-alerts/",
            "reports": "/api/v1/reports/drafts/",
        }


class EducationalDashboardView(RoleDashboardView):
    dashboard_name = "educational"
    accepted_roles = [Role.ORGANIZATION_ADMIN, Role.SCHOOL_MANAGER, Role.EDUCATIONAL_DEPUTY]

    def metrics(self, request, school_ids):
        offerings = CourseOffering.objects.filter(
            class_section__school_id__in=school_ids, is_active=True
        )
        assessments = Assessment.objects.filter(
            course_offering__in=offerings,
            status__in=[
                Assessment.Status.DRAFT,
                Assessment.Status.SUBMITTED,
                Assessment.Status.REJECTED,
            ],
        )
        assessment_rows = list(assessments.values("id", "course_offering__class_section_id"))
        active_by_class = defaultdict(set)
        for class_id, enrollment_id in Enrollment.objects.filter(
            class_section_id__in={
                row["course_offering__class_section_id"] for row in assessment_rows
            },
            status=Enrollment.Status.ACTIVE,
        ).values_list("class_section_id", "id"):
            active_by_class[class_id].add(enrollment_id)
        entered_by_assessment = defaultdict(set)
        for assessment_id, enrollment_id in (
            Score.objects.filter(assessment_id__in=[row["id"] for row in assessment_rows])
            .exclude(status=Score.Status.NOT_ENTERED)
            .values_list("assessment_id", "enrollment_id")
        ):
            entered_by_assessment[assessment_id].add(enrollment_id)
        missing_teacher_scores = sum(
            len(
                active_by_class[row["course_offering__class_section_id"]]
                - entered_by_assessment[row["id"]]
            )
            for row in assessment_rows
        )
        return {
            "active_students": Enrollment.objects.filter(
                school_id__in=school_ids, status=Enrollment.Status.ACTIVE
            ).count(),
            "open_assessments": assessments.count(),
            "missing_teacher_scores": missing_teacher_scores,
            "active_risk_signals": StudentRiskSignal.objects.filter(
                school_id__in=school_ids, state=StudentRiskSignal.State.ACTIVE
            ).count(),
        }

    def drill_down(self):
        return {"assessments": "/api/v1/assessments/", "signals": "/api/v1/analytics/risk-signals/"}


class StudentAffairsDashboardView(RoleDashboardView):
    dashboard_name = "student-affairs"
    accepted_roles = [Role.ORGANIZATION_ADMIN, Role.SCHOOL_MANAGER, Role.STUDENT_AFFAIRS_DEPUTY]

    def metrics(self, request, school_ids):
        return {
            "confirmed_behavior_events": BehaviorEvent.objects.filter(
                school_id__in=school_ids,
                status__in=[BehaviorEvent.Status.CONFIRMED, BehaviorEvent.Status.UNDER_FOLLOW_UP],
            ).count(),
            "behavior_follow_ups": BehaviorEvent.objects.filter(
                school_id__in=school_ids, status=BehaviorEvent.Status.UNDER_FOLLOW_UP
            ).count(),
            "open_operational_alerts": OperationalAlert.objects.filter(
                signal__school_id__in=school_ids, status=OperationalAlert.Status.OPEN
            ).count(),
        }

    def drill_down(self):
        return {
            "behavior": "/api/v1/behavior-events/",
            "alerts": "/api/v1/analytics/operational-alerts/",
        }


class CounselorDashboardView(RoleDashboardView):
    dashboard_name = "counselor"
    accepted_roles = [Role.COUNSELOR]
    strict_direct_role = True

    def metrics(self, request, school_ids):
        cases = CounselingCase.objects.filter(
            assigned_counselor=request.user, school_id__in=school_ids
        )
        # An aggregate dashboard access is still a confidential read.  Its audit
        # record has no case identifier, session content, or note text.
        AuditEvent.objects.create(
            actor=request.user,
            action="counseling.dashboard_viewed",
            entity_type="CounselingDashboard",
            organization_id=None,
            school_id=school_ids[0] if len(school_ids) == 1 else None,
            metadata={"scope": "counselor_dashboard", "school_count": len(school_ids)},
            request_id=request.headers.get("X-Request-ID", "")[:64],
        )
        return {
            "active_assigned_cases": cases.filter(status=CounselingCase.Status.ACTIVE).count(),
            "high_risk_assigned_cases": cases.filter(
                shared_risk_level__in=[
                    CounselingCase.RiskLevel.HIGH,
                    CounselingCase.RiskLevel.CRITICAL,
                ]
            ).count(),
            "pending_referrals": Referral.objects.filter(
                target_counselor=request.user,
                target_enrollment__school_id__in=school_ids,
                status=Referral.Status.SENT,
            ).count(),
        }

    def drill_down(self):
        return {"cases": "/api/v1/counseling/cases/", "referrals": "/api/v1/counseling/referrals/"}


class GuideTeacherDashboardView(RoleDashboardView):
    dashboard_name = "guide-teacher"
    accepted_roles = [Role.GUIDE_TEACHER]
    strict_direct_role = True

    def metrics(self, request, school_ids):
        assignments = GuideTeacherAssignment.objects.filter(
            guide_teacher=request.user, enrollment__school_id__in=school_ids, ends_at__isnull=True
        )
        return {
            "active_assignments": assignments.count(),
            "open_follow_ups": GuideFollowUp.objects.filter(
                assignment__in=assignments, status=GuideFollowUp.Status.OPEN
            ).count(),
            "released_action_plans": assignments.filter(action_plans__visibility="released")
            .distinct()
            .count(),
        }

    def drill_down(self):
        return {
            "assignments": "/api/v1/guide-teacher-assignments/",
            "follow_ups": "/api/v1/guide-follow-ups/",
        }


class TeacherDashboardView(RoleDashboardView):
    dashboard_name = "teacher"
    accepted_roles = [Role.TEACHER]

    def metrics(self, request, school_ids):
        offerings = CourseOffering.objects.filter(
            teacher=request.user, class_section__school_id__in=school_ids, is_active=True
        )
        assessments = Assessment.objects.filter(course_offering__in=offerings)
        return {
            "active_course_offerings": offerings.count(),
            "open_assessments": assessments.filter(
                status__in=[
                    Assessment.Status.DRAFT,
                    Assessment.Status.SUBMITTED,
                    Assessment.Status.REJECTED,
                ]
            ).count(),
            "locked_assessments": assessments.filter(status=Assessment.Status.LOCKED).count(),
        }

    def drill_down(self):
        return {"assessments": "/api/v1/assessments/", "attendance": "/api/v1/attendance-sessions/"}
