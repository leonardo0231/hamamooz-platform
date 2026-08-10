from uuid import UUID

from django.db import transaction
from django.db.models import Prefetch
from django.http import FileResponse
from django.utils.text import slugify
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from hamamooz.apps.accounts.access import allowed_class_ids, selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.accounts.permissions import RolePermission
from hamamooz.apps.core.services import record_audit
from hamamooz.apps.organizations.models import AcademicYear, ClassSection
from hamamooz.apps.students.models import Enrollment

from .catalog import FRAMEWORK_VERSION, METRIC_CATALOG
from .exports import build_evaluation_analytics_workbook
from .manual import delete_manual_evaluation, upsert_manual_evaluation
from .models import MonthlyEvaluation
from .serializers import (
    EvaluationCatalogSerializer,
    EvaluationDashboardSerializer,
    ManualEvaluationDeleteSerializer,
    ManualMonthlyEvaluationInputSerializer,
    ManualMonthlyEvaluationResponseSerializer,
    MonthlyEvaluationSerializer,
    StudentEvaluationAnalyticsSerializer,
)
from .services import EvaluationAnalyticsService

EVALUATION_WRITERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
    Role.OPERATOR,
    Role.TEACHER,
]


class MonthlyEvaluationViewSet(ReadOnlyModelViewSet):
    queryset = MonthlyEvaluation.objects.none()
    serializer_class = MonthlyEvaluationSerializer
    permission_classes = [RolePermission]
    required_roles_by_action = {
        "manual": EVALUATION_WRITERS,
        "manual_delete": EVALUATION_WRITERS,
    }
    filterset_fields = [
        "enrollment",
        "enrollment__student",
        "enrollment__academic_year",
        "enrollment__class_section",
        "month_no",
        "framework_version",
    ]
    search_fields = [
        "enrollment__student__first_name",
        "enrollment__student__last_name",
        "enrollment__student__national_id",
        "enrollment__student_number",
    ]
    ordering_fields = ["month_no", "created_at", "updated_at"]

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids(self.request.user, school_ids)
        return (
            MonthlyEvaluation.objects.filter(
                enrollment__school_id__in=school_ids,
                enrollment__class_section_id__in=class_ids,
            )
            .select_related(
                "enrollment__student",
                "enrollment__school__organization",
                "enrollment__academic_year",
                "enrollment__class_section",
                "recorded_by",
                "source_import_job",
            )
            .prefetch_related("metric_scores")
        )

    @extend_schema(responses={200: EvaluationCatalogSerializer})
    @action(detail=False, methods=["get"], url_path="catalog")
    def catalog(self, request):
        metrics = [
            {
                "code": code,
                "title": definition["title"],
                "domain_code": definition["domain_code"],
                "domain_title": definition["domain_title"],
                "domain_weight": definition["domain_weight"],
                "order": definition["order"],
            }
            for code, definition in METRIC_CATALOG.items()
        ]
        return Response(
            {
                "framework_version": FRAMEWORK_VERSION,
                "score_min": 0,
                "score_max": 5,
                "metric_count": len(metrics),
                "metrics": metrics,
            }
        )

    @extend_schema(
        request=ManualMonthlyEvaluationInputSerializer,
        responses={
            200: ManualMonthlyEvaluationResponseSerializer,
            201: ManualMonthlyEvaluationResponseSerializer,
        },
    )
    @action(detail=False, methods=["post"], url_path="manual")
    def manual(self, request):
        serializer = ManualMonthlyEvaluationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids(request.user, school_ids)
        try:
            enrollment = Enrollment.objects.select_related(
                "student", "school", "academic_year", "class_section"
            ).get(
                id=serializer.validated_data["enrollment"],
                school_id__in=school_ids,
                class_section_id__in=class_ids,
                status=Enrollment.Status.ACTIVE,
            )
        except Enrollment.DoesNotExist as exc:
            raise ValidationError(
                {"enrollment": "ثبت‌نام فعال انتخاب‌شده معتبر یا در حوزه دسترسی شما نیست."}
            ) from exc

        with transaction.atomic():
            evaluation, result = upsert_manual_evaluation(
                enrollment=enrollment,
                month_no=serializer.validated_data["month_no"],
                note=serializer.validated_data.get("note", ""),
                metrics=serializer.validated_data["metrics"],
                actor=request.user,
            )
            record_audit(
                action="evaluation.manual_upserted",
                actor=request.user,
                request=request,
                entity=evaluation,
                organization_id=enrollment.student.organization_id,
                school_id=enrollment.school_id,
                changes=result,
                metadata={
                    "month_no": evaluation.month_no,
                    "framework_version": evaluation.framework_version,
                    "metric_count": len(serializer.validated_data["metrics"]),
                },
            )

        evaluation = self.get_queryset().get(pk=evaluation.pk)
        return Response(
            {
                "evaluation": MonthlyEvaluationSerializer(evaluation).data,
                "result": result,
            },
            status=status.HTTP_201_CREATED if result["created"] else status.HTTP_200_OK,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="reason",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="دلیل حذف منطقی ارزیابی از نمای جاری.",
            )
        ],
        request=None,
        responses={204: None},
    )
    @action(detail=True, methods=["delete"], url_path="manual")
    def manual_delete(self, request, pk=None):
        evaluation = self.get_object()
        delete_data = request.data or {"reason": request.query_params.get("reason")}
        serializer = ManualEvaluationDeleteSerializer(data=delete_data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            deleted = delete_manual_evaluation(evaluation=evaluation)
            record_audit(
                action="evaluation.manual_deleted",
                actor=request.user,
                request=request,
                entity=deleted,
                organization_id=deleted.enrollment.student.organization_id,
                school_id=deleted.enrollment.school_id,
                metadata={
                    "month_no": deleted.month_no,
                    "framework_version": deleted.framework_version,
                    "reason": serializer.validated_data["reason"],
                },
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _cohort_enrollments(self):
        academic_year_id = self.request.query_params.get("academic_year")
        if not academic_year_id:
            raise ValidationError({"academic_year": "سال تحصیلی الزامی است."})
        try:
            UUID(str(academic_year_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValidationError({"academic_year": "شناسه سال تحصیلی معتبر نیست."}) from exc
        school_ids = selected_school_ids(self.request)
        if len(school_ids) != 1:
            raise ValidationError(
                {"X-School-ID": "برای تحلیل مدرسه باید دقیقاً یک شعبه انتخاب شود."}
            )
        class_ids = allowed_class_ids(self.request.user, school_ids)
        if not AcademicYear.objects.filter(
            id=academic_year_id,
            organization__schools__id__in=school_ids,
        ).exists():
            raise ValidationError({"academic_year": "سال تحصیلی معتبر یا قابل دسترس نیست."})
        queryset = Enrollment.objects.filter(
            school_id__in=school_ids,
            academic_year_id=academic_year_id,
            class_section_id__in=class_ids,
            status=Enrollment.Status.ACTIVE,
        )
        class_section_id = self.request.query_params.get("class_section")
        if class_section_id:
            try:
                UUID(str(class_section_id))
            except (ValueError, TypeError, AttributeError) as exc:
                raise ValidationError({"class_section": "شناسه کلاس معتبر نیست."}) from exc
            if not ClassSection.objects.filter(
                id=class_section_id,
                id__in=class_ids,
                school_id__in=school_ids,
                academic_year_id=academic_year_id,
            ).exists():
                raise ValidationError({"class_section": "کلاس انتخاب‌شده معتبر یا قابل دسترس نیست."})
            queryset = queryset.filter(class_section_id=class_section_id)
        evaluation_queryset = MonthlyEvaluation.objects.prefetch_related("metric_scores").order_by(
            "month_no"
        )
        enrollments = list(
            queryset.select_related(
                "student", "school", "academic_year", "class_section"
            ).prefetch_related(
                Prefetch(
                    "monthly_evaluations",
                    queryset=evaluation_queryset,
                    to_attr="_analytics_evaluations",
                )
            )
        )
        return enrollments, "class" if class_section_id else "school"

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="enrollment",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=True,
            ),
            OpenApiParameter(
                name="rank_scope",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=["school", "class"],
                required=False,
            ),
        ],
        responses={200: StudentEvaluationAnalyticsSerializer},
    )
    @action(detail=False, methods=["get"])
    def analytics(self, request):
        enrollment_id = request.query_params.get("enrollment")
        if not enrollment_id:
            raise ValidationError({"enrollment": "شناسه ثبت‌نام الزامی است."})
        try:
            UUID(str(enrollment_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValidationError({"enrollment": "شناسه ثبت‌نام معتبر نیست."}) from exc
        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids(request.user, school_ids)
        try:
            enrollment = Enrollment.objects.select_related(
                "student", "school", "academic_year", "class_section"
            ).get(
                id=enrollment_id,
                school_id__in=school_ids,
                class_section_id__in=class_ids,
            )
        except (Enrollment.DoesNotExist, ValueError, TypeError) as exc:
            raise ValidationError(
                {"enrollment": "ثبت‌نام انتخاب‌شده معتبر یا قابل دسترس نیست."}
            ) from exc
        rank_scope = request.query_params.get("rank_scope", "school")
        try:
            result = EvaluationAnalyticsService.student_summary(
                enrollment,
                rank_scope=rank_scope,
            )
        except ValueError as exc:
            raise ValidationError({"rank_scope": str(exc)}) from exc
        return Response(StudentEvaluationAnalyticsSerializer(result).data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="academic_year",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=True,
            ),
            OpenApiParameter(
                name="class_section",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
        ],
        responses={200: EvaluationDashboardSerializer},
    )
    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        enrollments, rank_scope = self._cohort_enrollments()
        result = EvaluationAnalyticsService.cohort_summary(
            enrollments,
            rank_scope=rank_scope,
        )
        return Response(EvaluationDashboardSerializer(result).data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="academic_year",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=True,
            ),
            OpenApiParameter(
                name="class_section",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
        ],
        responses={
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes
        },
    )
    @action(detail=False, methods=["get"])
    def export(self, request):
        enrollments, rank_scope = self._cohort_enrollments()
        cohort = EvaluationAnalyticsService.cohort_summary(
            enrollments,
            rank_scope=rank_scope,
        )
        output = build_evaluation_analytics_workbook(enrollments, cohort)
        academic_year = enrollments[0].academic_year.code if enrollments else "empty"
        class_code = (
            enrollments[0].class_section.code if rank_scope == "class" and enrollments else "school"
        )
        return FileResponse(
            output,
            as_attachment=True,
            filename=(f"evaluation-analytics-{slugify(academic_year)}-{slugify(class_code)}.xlsx"),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
