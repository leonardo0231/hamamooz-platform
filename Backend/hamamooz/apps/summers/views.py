from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from hamamooz.apps.accounts.access import broad_access_school_ids, selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.services import record_audit
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import (
    SummerComprehensiveExam,
    SummerCourse,
    SummerCourseRegistration,
    SummerProgram,
    SummerRegistration,
    SummerSubjectScore,
)
from .serializers import (
    SummerComprehensiveExamSerializer,
    SummerCourseRegistrationSerializer,
    SummerCourseSerializer,
    SummerProgramRevisionSerializer,
    SummerProgramSerializer,
    SummerRegistrationSerializer,
    SummerSubjectScoreSerializer,
)
from .services import validate_exam_completeness

SUMMER_MANAGERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
]
SUMMER_DATA_ENTRY = SUMMER_MANAGERS + [Role.OPERATOR]


def summer_data_school_ids(request):
    selected = selected_school_ids(request)
    return broad_access_school_ids(request.user, selected)


def ensure_program_roster_open(program):
    if program.exams.filter(status=SummerComprehensiveExam.Status.FINALIZED).exists():
        raise PermissionDenied("فهرست برنامه دارای آزمون جامع نهایی‌شده قابل تغییر نیست.")


def create_locked_roster_entry(viewset, serializer, program):
    """Serialize enrollment/roster writes with finalization on one program row."""
    with transaction.atomic():
        locked_program = SummerProgram.objects.select_for_update().get(pk=program.pk)
        ensure_program_roster_open(locked_program)
        try:
            serializer.Meta.model(**serializer.validated_data).full_clean(exclude=["id"])
        except DjangoValidationError as exc:
            raise ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            ) from exc
        viewset.perform_audited_create(serializer)


def delete_locked_roster_entry(viewset, instance, program):
    with transaction.atomic():
        locked_program = SummerProgram.objects.select_for_update().get(pk=program.pk)
        ensure_program_roster_open(locked_program)
        AuditedModelViewSet.perform_destroy(viewset, instance)


def lock_open_score_target(exam, course_registration):
    """Lock program before exam so score writes cannot race roster finalization."""
    program = SummerProgram.objects.select_for_update().get(pk=exam.program_id)
    locked_exam = SummerComprehensiveExam.objects.select_for_update().get(pk=exam.pk)
    if locked_exam.status != SummerComprehensiveExam.Status.DRAFT:
        raise PermissionDenied("نمره آزمون جامع نهایی‌شده قابل تغییر نیست.")
    locked_registration = (
        SummerCourseRegistration.objects.select_for_update()
        .filter(
            pk=course_registration.pk,
            registration__is_deleted=False,
            registration__program_id=program.pk,
            course__is_deleted=False,
            course__program_id=program.pk,
        )
        .first()
    )
    if locked_registration is None:
        raise ValidationError(
            {"course_registration": "ثبت‌نام درس تابستانی معتبر و فعال نیست."}
        )
    return locked_exam, locked_registration


class SummerProgramViewSet(AuditedModelViewSet):
    queryset = SummerProgram.objects.none()
    serializer_class = SummerProgramSerializer
    filterset_fields = ["school", "academic_year"]
    search_fields = ["title", "school__name", "academic_year__title"]
    ordering_fields = ["created_at", "title"]
    required_roles_by_action = {
        name: SUMMER_MANAGERS for name in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return SummerProgram.objects.filter(
            school_id__in=selected_school_ids(self.request)
        ).select_related("school__organization", "academic_year")

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        program = self.get_object()
        revisions = program.threshold_revisions.select_related("actor")
        return Response(SummerProgramRevisionSerializer(revisions, many=True).data)


class SummerCourseViewSet(AuditedModelViewSet):
    queryset = SummerCourse.objects.none()
    serializer_class = SummerCourseSerializer
    filterset_fields = ["program", "subject"]
    search_fields = ["subject__title", "subject__code"]
    ordering_fields = ["created_at", "subject__title"]
    required_roles_by_action = {
        name: SUMMER_MANAGERS for name in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return SummerCourse.objects.filter(
            program__school_id__in=selected_school_ids(self.request)
        ).select_related("program__school__organization", "program__academic_year", "subject")

    def perform_create(self, serializer):
        create_locked_roster_entry(self, serializer, serializer.validated_data["program"])

    def perform_destroy(self, instance):
        delete_locked_roster_entry(self, instance, instance.program)


class SummerRegistrationViewSet(AuditedModelViewSet):
    queryset = SummerRegistration.objects.none()
    serializer_class = SummerRegistrationSerializer
    filterset_fields = ["program", "enrollment"]
    search_fields = [
        "enrollment__student__first_name",
        "enrollment__student__last_name",
        "enrollment__student__national_id",
    ]
    ordering_fields = ["created_at", "enrollment__student__last_name"]
    required_roles_by_action = {
        name: SUMMER_DATA_ENTRY for name in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return SummerRegistration.objects.filter(
            program__school_id__in=summer_data_school_ids(self.request)
        ).select_related(
            "program__school__organization",
            "program__academic_year",
            "enrollment__student",
            "enrollment__grade_level",
            "enrollment__class_section",
        )

    def perform_create(self, serializer):
        create_locked_roster_entry(self, serializer, serializer.validated_data["program"])

    def perform_destroy(self, instance):
        delete_locked_roster_entry(self, instance, instance.program)


class SummerCourseRegistrationViewSet(AuditedModelViewSet):
    queryset = SummerCourseRegistration.objects.none()
    serializer_class = SummerCourseRegistrationSerializer
    filterset_fields = ["registration", "course"]
    search_fields = [
        "registration__enrollment__student__first_name",
        "registration__enrollment__student__last_name",
        "course__subject__title",
    ]
    ordering_fields = ["created_at", "course__subject__title"]
    required_roles_by_action = {
        name: SUMMER_DATA_ENTRY for name in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return SummerCourseRegistration.objects.filter(
            registration__program__school_id__in=summer_data_school_ids(self.request)
        ).select_related(
            "registration__program__school__organization",
            "registration__enrollment__student",
            "course__subject",
        )

    def perform_create(self, serializer):
        create_locked_roster_entry(
            self,
            serializer,
            serializer.validated_data["registration"].program,
        )

    def perform_destroy(self, instance):
        delete_locked_roster_entry(self, instance, instance.registration.program)


class SummerComprehensiveExamViewSet(AuditedModelViewSet):
    queryset = SummerComprehensiveExam.objects.none()
    serializer_class = SummerComprehensiveExamSerializer
    filterset_fields = ["program", "status", "exam_date"]
    search_fields = ["title", "program__title"]
    ordering_fields = ["exam_date", "created_at", "title"]
    required_roles_by_action = {
        name: SUMMER_MANAGERS
        for name in ["create", "update", "partial_update", "destroy", "finalize"]
    }

    def get_queryset(self):
        return SummerComprehensiveExam.objects.filter(
            program__school_id__in=selected_school_ids(self.request)
        ).select_related(
            "program__school__organization", "program__academic_year", "finalized_by"
        )

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        with transaction.atomic():
            requested_exam = self.get_object()
            SummerProgram.objects.select_for_update().get(pk=requested_exam.program_id)
            exam = (
                SummerComprehensiveExam.objects.select_for_update()
                .select_related("program__school__organization", "program__academic_year")
                .get(pk=requested_exam.pk)
            )
            self.check_object_permissions(request, exam)
            if exam.status == SummerComprehensiveExam.Status.FINALIZED:
                return Response(self.get_serializer(exam).data)
            validate_exam_completeness(exam)
            exam.status = SummerComprehensiveExam.Status.FINALIZED
            exam.finalized_at = timezone.now()
            exam.finalized_by = request.user
            exam.save(update_fields=["status", "finalized_at", "finalized_by", "updated_at"])
            record_audit(
                action="summer_exam.finalized",
                actor=request.user,
                request=request,
                entity=exam,
                organization_id=exam.organization_id,
                school_id=exam.school_id,
            )
        return Response(self.get_serializer(exam).data)


class SummerSubjectScoreViewSet(AuditedModelViewSet):
    queryset = SummerSubjectScore.objects.none()
    serializer_class = SummerSubjectScoreSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["exam", "course_registration"]
    search_fields = [
        "course_registration__registration__enrollment__student__first_name",
        "course_registration__registration__enrollment__student__last_name",
        "course_registration__course__subject__title",
    ]
    ordering_fields = ["created_at", "course_registration__course__subject__title"]
    required_roles_by_action = {
        name: SUMMER_DATA_ENTRY for name in ["create", "update", "partial_update"]
    }

    def get_queryset(self):
        return SummerSubjectScore.objects.filter(
            exam__program__school_id__in=summer_data_school_ids(self.request)
        ).select_related(
            "exam__program__school__organization",
            "course_registration__registration__enrollment__student",
            "course_registration__course__subject",
            "recorded_by",
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            exam, course_registration = lock_open_score_target(
                serializer.validated_data["exam"],
                serializer.validated_data["course_registration"],
            )
            serializer.validated_data["exam"] = exam
            serializer.validated_data["course_registration"] = course_registration
            try:
                SummerSubjectScore(
                    **serializer.validated_data,
                    recorded_by=self.request.user,
                ).full_clean(exclude=["id"])
            except DjangoValidationError as exc:
                raise ValidationError(
                    exc.message_dict if hasattr(exc, "message_dict") else exc.messages
                ) from exc
            self.perform_audited_create(
                serializer,
                action="summer_score.recorded",
                recorded_by=self.request.user,
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            lock_open_score_target(
                serializer.instance.exam,
                serializer.instance.course_registration,
            )
            super().perform_update(serializer)
