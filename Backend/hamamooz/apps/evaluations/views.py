from uuid import UUID

from django.db.models import Prefetch
from django.http import FileResponse
from django.utils.text import slugify
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from hamamooz.apps.accounts.access import allowed_class_ids, selected_school_ids
from hamamooz.apps.accounts.permissions import RolePermission
from hamamooz.apps.organizations.models import AcademicYear, ClassSection
from hamamooz.apps.students.models import Enrollment

from .exports import build_evaluation_analytics_workbook
from .models import MonthlyEvaluation
from .serializers import (
    EvaluationDashboardSerializer,
    MonthlyEvaluationSerializer,
    StudentEvaluationAnalyticsSerializer,
)
from .services import EvaluationAnalyticsService


class MonthlyEvaluationViewSet(ReadOnlyModelViewSet):
    queryset = MonthlyEvaluation.objects.none()
    serializer_class = MonthlyEvaluationSerializer
    permission_classes = [RolePermission]
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
