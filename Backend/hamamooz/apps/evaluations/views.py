from rest_framework.viewsets import ReadOnlyModelViewSet

from hamamooz.apps.accounts.access import selected_school_ids
from hamamooz.apps.accounts.permissions import RolePermission

from .models import MonthlyEvaluation
from .serializers import MonthlyEvaluationSerializer


class MonthlyEvaluationViewSet(ReadOnlyModelViewSet):
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
        return (
            MonthlyEvaluation.objects.filter(
                enrollment__school_id__in=selected_school_ids(self.request)
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
