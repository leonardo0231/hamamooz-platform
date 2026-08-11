from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from hamamooz.apps.accounts.access import allowed_class_ids, selected_school_ids, user_has_role
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.services import record_audit
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import Enrollment, Guardian, Student, StudentGuardian
from .selectors import (
    build_student_360_academics,
    build_student_360_activities,
    build_student_360_attendance,
    build_student_360_behavior,
    build_student_360_evaluations,
    build_student_360_recommendations,
    build_student_360_reports,
    build_student_360_risks,
    build_student_360_summary,
)
from .serializers import (
    ChangeClassSerializer,
    ChangeEnrollmentStatusSerializer,
    EnrollmentSerializer,
    GuardianSerializer,
    LinkGuardianSerializer,
    Student360AcademicsSerializer,
    Student360ActivitiesSerializer,
    Student360AttendanceSerializer,
    Student360BehaviorSerializer,
    Student360EvaluationsSerializer,
    Student360RecommendationsSerializer,
    Student360ReportsSerializer,
    Student360RisksSerializer,
    Student360SummarySerializer,
    StudentSerializer,
    TransferEnrollmentSerializer,
)
from .services import change_class, change_status, transfer_enrollment

STUDENT_WRITERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
    Role.OPERATOR,
]


class StudentViewSet(AuditedModelViewSet):
    queryset = Student.objects.none()
    serializer_class = StudentSerializer
    search_fields = ["national_id", "first_name", "last_name"]
    filterset_fields = [
        "organization",
        "gender",
        "status",
        "enrollments__academic_year",
        "enrollments__class_section",
    ]
    required_roles_by_action = {
        action: STUDENT_WRITERS
        for action in ["create", "update", "partial_update", "destroy", "link_guardian"]
    }

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids(self.request.user, school_ids)
        return (
            Student.objects.filter(
                enrollments__school_id__in=school_ids,
                enrollments__class_section_id__in=class_ids,
            )
            .select_related("organization")
            .prefetch_related("guardian_links__guardian")
            .distinct()
        )

    @extend_schema(responses={200: Student360SummarySerializer})
    @action(detail=True, methods=["get"], url_path="360/summary")
    def student_360_summary(self, request, pk=None):
        student = self.get_object()
        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids(request.user, school_ids)
        summary = build_student_360_summary(
            student=student,
            school_ids=school_ids,
            class_ids=class_ids,
        )
        return Response(Student360SummarySerializer(summary).data)

    @extend_schema(responses={200: Student360AcademicsSerializer})
    @action(detail=True, methods=["get"], url_path="360/academics")
    def student_360_academics(self, request, pk=None):
        student = self.get_object()
        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids(request.user, school_ids)
        academics = build_student_360_academics(
            student=student,
            school_ids=school_ids,
            class_ids=class_ids,
        )
        return Response(Student360AcademicsSerializer(academics).data)

    @extend_schema(responses={200: Student360AttendanceSerializer})
    @action(detail=True, methods=["get"], url_path="360/attendance")
    def student_360_attendance(self, request, pk=None):
        student = self.get_object()
        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids(request.user, school_ids)
        attendance = build_student_360_attendance(
            student=student,
            school_ids=school_ids,
            class_ids=class_ids,
        )
        return Response(Student360AttendanceSerializer(attendance).data)

    @extend_schema(responses={200: Student360EvaluationsSerializer})
    @action(detail=True, methods=["get"], url_path="360/evaluations")
    def student_360_evaluations(self, request, pk=None):
        student = self.get_object()
        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids(request.user, school_ids)
        evaluations = build_student_360_evaluations(
            student=student,
            school_ids=school_ids,
            class_ids=class_ids,
        )
        return Response(Student360EvaluationsSerializer(evaluations).data)

    @extend_schema(responses={200: Student360ReportsSerializer})
    @action(detail=True, methods=["get"], url_path="360/reports")
    def student_360_reports(self, request, pk=None):
        student = self.get_object()
        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids(request.user, school_ids)
        reports = build_student_360_reports(
            student=student,
            school_ids=school_ids,
            class_ids=class_ids,
        )
        return Response(Student360ReportsSerializer(reports, context={"request": request}).data)

    @extend_schema(responses={200: Student360BehaviorSerializer})
    @action(detail=True, methods=["get"], url_path="360/behavior")
    def student_360_behavior(self, request, pk=None):
        student = self.get_object()
        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids(request.user, school_ids)
        behavior = build_student_360_behavior(
            student=student,
            school_ids=school_ids,
            class_ids=class_ids,
        )
        return Response(Student360BehaviorSerializer(behavior).data)

    @extend_schema(responses={200: Student360ActivitiesSerializer})
    @action(detail=True, methods=["get"], url_path="360/activities")
    def student_360_activities(self, request, pk=None):
        student = self.get_object()
        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids(request.user, school_ids)
        activities = build_student_360_activities(
            student=student,
            school_ids=school_ids,
            class_ids=class_ids,
        )
        return Response(Student360ActivitiesSerializer(activities).data)

    @extend_schema(responses={200: Student360RisksSerializer})
    @action(detail=True, methods=["get"], url_path="360/risks")
    def student_360_risks(self, request, pk=None):
        student = self.get_object()
        risks = build_student_360_risks(
            student=student,
            school_ids=selected_school_ids(request),
            class_ids=allowed_class_ids(request.user, selected_school_ids(request)),
        )
        return Response(Student360RisksSerializer(risks).data)

    @extend_schema(responses={200: Student360RecommendationsSerializer})
    @action(detail=True, methods=["get"], url_path="360/recommendations")
    def student_360_recommendations(self, request, pk=None):
        student = self.get_object()
        recommendations = build_student_360_recommendations(
            student=student,
            school_ids=selected_school_ids(request),
            class_ids=allowed_class_ids(request.user, selected_school_ids(request)),
        )
        return Response(Student360RecommendationsSerializer(recommendations).data)

    @action(detail=True, methods=["post"], url_path="guardians")
    def link_guardian(self, request, pk=None):
        student = self.get_object()
        serializer = LinkGuardianSerializer(data=request.data, context={"student": student})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            link, created = StudentGuardian.objects.update_or_create(
                student=student,
                guardian=serializer.validated_data["guardian"],
                defaults={
                    "relationship": serializer.validated_data["relationship"],
                    "is_primary": serializer.validated_data["is_primary"],
                    "can_pick_up": serializer.validated_data["can_pick_up"],
                },
            )
            record_audit(
                action="student.guardian_linked",
                actor=request.user,
                request=request,
                entity=student,
                organization_id=student.organization_id,
                changes={"guardian_id": str(link.guardian_id), "created": created},
            )
        return Response(
            StudentSerializer(student).data, status=status.HTTP_201_CREATED if created else 200
        )


class GuardianViewSet(AuditedModelViewSet):
    queryset = Guardian.objects.none()
    serializer_class = GuardianSerializer
    search_fields = ["national_id", "first_name", "last_name", "phone_primary"]
    filterset_fields = ["organization"]
    required_roles_by_action = {
        action: STUDENT_WRITERS for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids(self.request.user, school_ids)
        return (
            Guardian.objects.filter(
                student_links__student__enrollments__school_id__in=school_ids,
                student_links__student__enrollments__class_section_id__in=class_ids,
            )
            .select_related("organization")
            .distinct()
        )


class EnrollmentViewSet(AuditedModelViewSet):
    queryset = Enrollment.objects.none()
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = EnrollmentSerializer
    search_fields = [
        "student__national_id",
        "student__first_name",
        "student__last_name",
        "student_number",
    ]
    filterset_fields = ["school", "academic_year", "grade_level", "class_section", "status"]
    required_roles_by_action = {
        action: STUDENT_WRITERS
        for action in [
            "create",
            "change_class",
            "transfer",
            "change_status",
        ]
    }

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids(self.request.user, school_ids)
        return (
            Enrollment.objects.filter(school_id__in=school_ids, class_section_id__in=class_ids)
            .select_related(
                "student",
                "school__organization",
                "academic_year",
                "grade_level",
                "class_section",
            )
            .prefetch_related("events__actor")
        )

    @action(detail=True, methods=["post"], url_path="change-class")
    def change_class(self, request, pk=None):
        enrollment = self.get_object()
        serializer = ChangeClassSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            updated = change_class(
                enrollment=enrollment,
                new_class=serializer.validated_data["class_section"],
                reason=serializer.validated_data["reason"],
                effective_date=serializer.validated_data.get("effective_date"),
                actor=request.user,
            )
            record_audit(
                action="enrollment.class_changed",
                actor=request.user,
                request=request,
                entity=updated,
                school_id=updated.school_id,
                changes={"from_enrollment_id": str(enrollment.id)},
            )
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        enrollment = self.get_object()
        serializer = TransferEnrollmentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        target_school = serializer.validated_data["school"]
        if not user_has_role(
            request.user,
            STUDENT_WRITERS,
            organization_id=target_school.organization_id,
            school_id=target_school.id,
        ):
            self.permission_denied(request, "در شعبه مقصد مجوز ثبت‌نام ندارید.")
        with transaction.atomic():
            target = transfer_enrollment(
                enrollment=enrollment, actor=request.user, **serializer.validated_data
            )
            record_audit(
                action="enrollment.transferred",
                actor=request.user,
                request=request,
                entity=target,
                organization_id=target.student.organization_id,
                school_id=target.school_id,
                changes={"from_enrollment_id": str(enrollment.id)},
            )
        return Response(self.get_serializer(target).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        enrollment = self.get_object()
        serializer = ChangeEnrollmentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            updated = change_status(
                enrollment=enrollment,
                new_status=serializer.validated_data["status"],
                date=serializer.validated_data["date"],
                reason=serializer.validated_data["reason"],
                actor=request.user,
            )
            record_audit(
                action="enrollment.status_changed",
                actor=request.user,
                request=request,
                entity=updated,
                school_id=updated.school_id,
            )
        return Response(self.get_serializer(updated).data)
