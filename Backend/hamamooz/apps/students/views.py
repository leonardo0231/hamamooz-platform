from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from hamamooz.apps.accounts.access import allowed_class_ids, selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.services import record_audit
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import Enrollment, Guardian, Student, StudentGuardian
from .serializers import (
    ChangeClassSerializer,
    ChangeEnrollmentStatusSerializer,
    EnrollmentSerializer,
    GuardianSerializer,
    LinkGuardianSerializer,
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
            .prefetch_related("guardian_links__guardian")
            .distinct()
        )

    @action(detail=True, methods=["post"], url_path="guardians")
    def link_guardian(self, request, pk=None):
        student = self.get_object()
        serializer = LinkGuardianSerializer(data=request.data, context={"student": student})
        serializer.is_valid(raise_exception=True)
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
        return Guardian.objects.filter(
            student_links__student__enrollments__school_id__in=school_ids,
            student_links__student__enrollments__class_section_id__in=class_ids,
        ).distinct()


class EnrollmentViewSet(AuditedModelViewSet):
    queryset = Enrollment.objects.none()
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
            "update",
            "partial_update",
            "destroy",
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
            .select_related("student", "school", "academic_year", "grade_level", "class_section")
            .prefetch_related("events__actor")
        )

    @action(detail=True, methods=["post"], url_path="change-class")
    def change_class(self, request, pk=None):
        enrollment = self.get_object()
        serializer = ChangeClassSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = change_class(
            enrollment=enrollment,
            new_class=serializer.validated_data["class_section"],
            reason=serializer.validated_data["reason"],
            actor=request.user,
        )
        record_audit(
            action="enrollment.class_changed",
            actor=request.user,
            request=request,
            entity=updated,
            school_id=updated.school_id,
        )
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        enrollment = self.get_object()
        serializer = TransferEnrollmentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
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
