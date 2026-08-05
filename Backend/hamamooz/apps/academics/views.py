from django.db import transaction
from django.db.models import Count, Q
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from hamamooz.apps.accounts.access import (
    accessible_organization_ids,
    broad_access_school_ids,
    selected_school_ids,
)
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.accounts.permissions import RolePermission
from hamamooz.apps.core.services import record_audit
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import (
    Assessment,
    AssessmentType,
    CalculationPolicy,
    CourseOffering,
    GradeSubject,
    Score,
    Subject,
    SubjectResult,
)
from .serializers import (
    AssessmentSerializer,
    AssessmentTypeSerializer,
    BulkScoreSerializer,
    CalculationPolicySerializer,
    CorrectLockedScoreSerializer,
    CourseOfferingSerializer,
    GradeSubjectSerializer,
    RejectAssessmentSerializer,
    ScoreSerializer,
    SubjectResultSerializer,
    SubjectSerializer,
)
from .services import (
    approve_assessment,
    bulk_upsert_scores,
    correct_locked_score,
    lock_assessment,
    reject_assessment,
    submit_assessment,
)
from .tasks import recalculate_class_term_task

ORG_ACADEMIC_ADMIN = [Role.SYSTEM_ADMIN, Role.ORGANIZATION_ADMIN, Role.EDUCATIONAL_DEPUTY]
SCHOOL_ACADEMIC_ADMIN = ORG_ACADEMIC_ADMIN + [Role.SCHOOL_MANAGER, Role.OPERATOR]
TEACHER_WRITERS = SCHOOL_ACADEMIC_ADMIN + [Role.TEACHER]
REVIEWERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
]


def offering_scope_q(user, school_ids, prefix=""):
    broad = broad_access_school_ids(user, school_ids)
    return Q(**{f"{prefix}class_section__school_id__in": broad}) | Q(
        **{f"{prefix}teacher": user, f"{prefix}class_section__school_id__in": school_ids}
    )


class SubjectViewSet(AuditedModelViewSet):
    queryset = Subject.objects.none()
    serializer_class = SubjectSerializer
    search_fields = ["title", "code"]
    filterset_fields = ["organization", "is_active"]
    required_roles_by_action = {
        action: ORG_ACADEMIC_ADMIN for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return Subject.objects.filter(
            organization_id__in=accessible_organization_ids(self.request.user)
        ).select_related("organization")


class GradeSubjectViewSet(AuditedModelViewSet):
    queryset = GradeSubject.objects.none()
    serializer_class = GradeSubjectSerializer
    search_fields = ["subject__title", "grade_level__title"]
    filterset_fields = ["grade_level", "subject", "is_active"]
    required_roles_by_action = {
        action: ORG_ACADEMIC_ADMIN for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return GradeSubject.objects.filter(
            grade_level__organization_id__in=accessible_organization_ids(self.request.user)
        ).select_related("grade_level", "subject")


class CourseOfferingViewSet(AuditedModelViewSet):
    queryset = CourseOffering.objects.none()
    serializer_class = CourseOfferingSerializer
    search_fields = ["grade_subject__subject__title", "class_section__title", "teacher__last_name"]
    filterset_fields = ["class_section", "grade_subject", "term", "teacher", "is_active"]
    required_roles_by_action = {
        action: SCHOOL_ACADEMIC_ADMIN
        for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        schools = selected_school_ids(self.request)
        return CourseOffering.objects.filter(
            offering_scope_q(self.request.user, schools)
        ).select_related(
            "class_section__school__organization",
            "grade_subject__subject",
            "term",
            "teacher",
        )

    @action(detail=True, methods=["get"])
    def results(self, request, pk=None):
        offering = self.get_object()
        queryset = SubjectResult.objects.filter(course_offering=offering).select_related(
            "enrollment__student", "course_offering__grade_subject__subject"
        )
        return Response(SubjectResultSerializer(queryset, many=True).data)


class AssessmentTypeViewSet(AuditedModelViewSet):
    queryset = AssessmentType.objects.none()
    serializer_class = AssessmentTypeSerializer
    search_fields = ["title", "code"]
    filterset_fields = ["organization", "category", "is_active"]
    required_roles_by_action = {
        action: ORG_ACADEMIC_ADMIN for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return AssessmentType.objects.filter(
            organization_id__in=accessible_organization_ids(self.request.user)
        ).select_related("organization")


class AssessmentViewSet(AuditedModelViewSet):
    queryset = Assessment.objects.none()
    serializer_class = AssessmentSerializer
    search_fields = ["title", "course_offering__grade_subject__subject__title"]
    filterset_fields = ["course_offering", "assessment_type", "status", "assessment_date"]
    required_roles_by_action = {
        "create": TEACHER_WRITERS,
        "update": TEACHER_WRITERS,
        "partial_update": TEACHER_WRITERS,
        "destroy": TEACHER_WRITERS,
        "bulk_scores": TEACHER_WRITERS,
        "submit": TEACHER_WRITERS,
        "approve": REVIEWERS,
        "reject": REVIEWERS,
        "lock": REVIEWERS,
    }

    def get_queryset(self):
        schools = selected_school_ids(self.request)
        return (
            Assessment.objects.filter(
                offering_scope_q(self.request.user, schools, prefix="course_offering__")
            )
            .select_related(
                "course_offering__class_section__school",
                "course_offering__class_section__school__organization",
                "course_offering__grade_subject__subject",
                "course_offering__teacher",
                "assessment_type",
                "created_by",
                "reviewed_by",
            )
            .annotate(score_count=Count("scores"))
        )

    def perform_create(self, serializer):
        self.perform_audited_create(
            serializer,
            action="assessment.created",
            created_by=self.request.user,
        )

    def perform_update(self, serializer):
        self._ensure_owner_or_broad(self.get_object())
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._ensure_owner_or_broad(instance)
        if instance.status not in [Assessment.Status.DRAFT, Assessment.Status.REJECTED]:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("فقط ارزیابی پیش‌نویس یا ردشده قابل حذف است.")
        super().perform_destroy(instance)

    def _ensure_owner_or_broad(self, assessment):
        school = assessment.course_offering.class_section.school
        broad = broad_access_school_ids(self.request.user, [school.id])
        if assessment.course_offering.teacher_id != self.request.user.id and school.id not in set(
            broad
        ):
            self.permission_denied(self.request, "دبیر فقط به ارزیابی درس خودش دسترسی نوشتن دارد.")

    @action(detail=True, methods=["get"])
    def scores(self, request, pk=None):
        assessment = self.get_object()
        queryset = assessment.scores.select_related(
            "enrollment__student", "recorded_by"
        ).prefetch_related("history__changed_by")
        return Response(ScoreSerializer(queryset, many=True).data)

    @action(detail=True, methods=["post"], url_path="scores/bulk")
    def bulk_scores(self, request, pk=None):
        assessment = self.get_object()
        self._ensure_owner_or_broad(assessment)
        serializer = BulkScoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            scores = bulk_upsert_scores(
                assessment=assessment,
                entries=serializer.validated_data["entries"],
                actor=request.user,
            )
            record_audit(
                action="assessment.scores_bulk_saved",
                actor=request.user,
                request=request,
                entity=assessment,
                school_id=assessment.school_id,
                changes={"score_count": len(scores)},
            )
        return Response(ScoreSerializer(scores, many=True).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        assessment = self.get_object()
        self._ensure_owner_or_broad(assessment)
        with transaction.atomic():
            updated = submit_assessment(assessment, request.user)
            record_audit(
                action="assessment.submitted",
                actor=request.user,
                request=request,
                entity=updated,
                school_id=updated.school_id,
            )
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        with transaction.atomic():
            updated = approve_assessment(self.get_object(), request.user)
            record_audit(
                action="assessment.approved",
                actor=request.user,
                request=request,
                entity=updated,
                school_id=updated.school_id,
            )
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = RejectAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            updated = reject_assessment(
                self.get_object(), request.user, serializer.validated_data["reason"]
            )
            record_audit(
                action="assessment.rejected",
                actor=request.user,
                request=request,
                entity=updated,
                school_id=updated.school_id,
                changes={"reason": serializer.validated_data["reason"]},
            )
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        with transaction.atomic():
            updated = lock_assessment(self.get_object(), request.user)
            class_id = str(updated.course_offering.class_section_id)
            term_id = str(updated.course_offering.term_id)
            transaction.on_commit(lambda: recalculate_class_term_task.delay(class_id, term_id))
            record_audit(
                action="assessment.locked",
                actor=request.user,
                request=request,
                entity=updated,
                school_id=updated.school_id,
            )
        return Response(self.get_serializer(updated).data)


class ScoreViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Score.objects.none()
    serializer_class = ScoreSerializer
    permission_classes = [RolePermission]
    filterset_fields = ["assessment", "enrollment", "status"]
    search_fields = ["enrollment__student__national_id", "enrollment__student__last_name"]
    required_roles_by_action = {"correct_locked": REVIEWERS}

    def get_queryset(self):
        schools = selected_school_ids(self.request)
        return Score.objects.filter(
            offering_scope_q(self.request.user, schools, prefix="assessment__course_offering__")
        ).select_related(
            "assessment__course_offering__class_section", "enrollment__student", "recorded_by"
        )

    @action(detail=True, methods=["post"], url_path="correct-locked")
    def correct_locked(self, request, pk=None):
        score = self.get_object()
        serializer = CorrectLockedScoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            updated = correct_locked_score(
                score=score, actor=request.user, **serializer.validated_data
            )
            transaction.on_commit(
                lambda: recalculate_class_term_task.delay(
                    str(updated.assessment.course_offering.class_section_id),
                    str(updated.assessment.course_offering.term_id),
                )
            )
            record_audit(
                action="score.locked_corrected",
                actor=request.user,
                request=request,
                entity=updated,
                school_id=updated.school_id,
                changes={"reason": serializer.validated_data["reason"]},
            )
        return Response(self.get_serializer(updated).data)


class CalculationPolicyViewSet(AuditedModelViewSet):
    queryset = CalculationPolicy.objects.none()
    serializer_class = CalculationPolicySerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["organization", "academic_year", "grade_level", "is_active"]
    required_roles_by_action = {"create": ORG_ACADEMIC_ADMIN}

    def get_queryset(self):
        return CalculationPolicy.objects.filter(
            organization_id__in=accessible_organization_ids(self.request.user)
        ).select_related("organization", "academic_year", "grade_level")
