from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .catalog import METRIC_CATALOG
from .models import MetricScore, MonthlyEvaluation
from .services import EvaluationAnalyticsService


class MetricScoreSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    domain_code = serializers.SerializerMethodField()
    domain_title = serializers.SerializerMethodField()

    class Meta:
        model = MetricScore
        fields = ["metric_code", "title", "domain_code", "domain_title", "value"]

    def _definition(self, obj):
        return METRIC_CATALOG[obj.metric_code]

    def get_title(self, obj) -> str:
        return self._definition(obj)["title"]

    def get_domain_code(self, obj) -> str:
        return self._definition(obj)["domain_code"]

    def get_domain_title(self, obj) -> str:
        return self._definition(obj)["domain_title"]


class DomainScoreSerializer(serializers.Serializer):
    code = serializers.CharField()
    title = serializers.CharField()
    weight = serializers.IntegerField()
    score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    completed_metrics = serializers.IntegerField()
    total_metrics = serializers.IntegerField()


class AnalyticsDomainSerializer(serializers.Serializer):
    code = serializers.CharField()
    title = serializers.CharField()
    score = serializers.FloatField(allow_null=True)


class MonthlyAnalyticsPointSerializer(serializers.Serializer):
    month_no = serializers.IntegerField(min_value=1, max_value=12)
    overall_score = serializers.FloatField(allow_null=True)
    completion_percent = serializers.FloatField()
    completion_status = serializers.ChoiceField(choices=["provisional", "final"])


class StudentEvaluationAnalyticsSerializer(serializers.Serializer):
    enrollment = serializers.UUIDField()
    student = serializers.UUIDField()
    student_name = serializers.CharField()
    student_number = serializers.CharField()
    school = serializers.UUIDField()
    academic_year = serializers.UUIDField()
    class_section = serializers.UUIDField()
    completion_status = serializers.ChoiceField(choices=["provisional", "final"])
    completion_percent = serializers.FloatField()
    overall_score = serializers.FloatField(allow_null=True)
    performance_level = serializers.CharField(allow_null=True)
    first_month = serializers.IntegerField(min_value=1, max_value=12, allow_null=True)
    last_month = serializers.IntegerField(min_value=1, max_value=12, allow_null=True)
    change = serializers.FloatField(allow_null=True)
    trend = serializers.ChoiceField(
        choices=["improving", "stable", "declining", "insufficient_data"]
    )
    trend_label = serializers.CharField()
    strongest_domain = AnalyticsDomainSerializer(allow_null=True)
    weakest_domain = AnalyticsDomainSerializer(allow_null=True)
    recommendation = serializers.CharField(allow_null=True)
    completion_warning = serializers.CharField(allow_null=True)
    monthly_scores = MonthlyAnalyticsPointSerializer(many=True)
    domain_scores = AnalyticsDomainSerializer(many=True)
    rank_scope = serializers.ChoiceField(choices=["school", "class"])
    rank = serializers.IntegerField(min_value=1, allow_null=True)
    ranked_count = serializers.IntegerField(min_value=0)


class CohortCountsSerializer(serializers.Serializer):
    students = serializers.IntegerField(min_value=0)
    evaluated = serializers.IntegerField(min_value=0)
    final = serializers.IntegerField(min_value=0)
    provisional = serializers.IntegerField(min_value=0)
    ranked = serializers.IntegerField(min_value=0)


class CohortMonthlyPointSerializer(serializers.Serializer):
    month_no = serializers.IntegerField(min_value=1, max_value=12)
    average = serializers.FloatField()
    students = serializers.IntegerField(min_value=0)


class CohortDomainSerializer(serializers.Serializer):
    code = serializers.CharField()
    title = serializers.CharField()
    average = serializers.FloatField(allow_null=True)


class EvaluationDashboardSerializer(serializers.Serializer):
    rank_scope = serializers.ChoiceField(choices=["school", "class"])
    counts = CohortCountsSerializer()
    monthly_trend = CohortMonthlyPointSerializer(many=True)
    domain_scores = CohortDomainSerializer(many=True)
    performance_distribution = serializers.DictField(child=serializers.IntegerField(min_value=0))
    students = StudentEvaluationAnalyticsSerializer(many=True)


class MonthlyEvaluationSerializer(serializers.ModelSerializer):
    student = serializers.UUIDField(source="enrollment.student_id", read_only=True)
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)
    student_number = serializers.CharField(source="enrollment.student_number", read_only=True)
    school = serializers.UUIDField(source="enrollment.school_id", read_only=True)
    school_name = serializers.CharField(source="enrollment.school.name", read_only=True)
    organization_name = serializers.CharField(
        source="enrollment.school.organization.name", read_only=True
    )
    academic_year = serializers.UUIDField(source="enrollment.academic_year_id", read_only=True)
    academic_year_title = serializers.CharField(
        source="enrollment.academic_year.title", read_only=True
    )
    class_title = serializers.CharField(source="enrollment.class_section.title", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)
    metric_scores = MetricScoreSerializer(many=True, read_only=True)
    domain_scores = serializers.SerializerMethodField()
    overall_score = serializers.SerializerMethodField()
    completion_percent = serializers.SerializerMethodField()
    completion_status = serializers.SerializerMethodField()
    performance_level = serializers.SerializerMethodField()
    completion_warning = serializers.SerializerMethodField()

    class Meta:
        model = MonthlyEvaluation
        fields = [
            "id",
            "enrollment",
            "student",
            "student_name",
            "student_number",
            "school",
            "school_name",
            "organization_name",
            "academic_year",
            "academic_year_title",
            "class_title",
            "month_no",
            "framework_version",
            "note",
            "recorded_by",
            "recorded_by_name",
            "source_import_job",
            "metric_scores",
            "domain_scores",
            "overall_score",
            "completion_percent",
            "completion_status",
            "performance_level",
            "completion_warning",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _summary(self, obj):
        summary = getattr(obj, "_evaluation_summary", None)
        if summary is None:
            summary = EvaluationAnalyticsService.evaluation_summary(obj)
            obj._evaluation_summary = summary
        return summary

    @extend_schema_field(DomainScoreSerializer(many=True))
    def get_domain_scores(self, obj) -> list[dict]:
        return self._summary(obj)["domain_scores"]

    @extend_schema_field(serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True))
    def get_overall_score(self, obj) -> float | None:
        return self._summary(obj)["overall_score"]

    @extend_schema_field(serializers.DecimalField(max_digits=5, decimal_places=2))
    def get_completion_percent(self, obj) -> float:
        return self._summary(obj)["completion_percent"]

    @extend_schema_field(serializers.ChoiceField(choices=["provisional", "final"]))
    def get_completion_status(self, obj) -> str:
        return self._summary(obj)["completion_status"]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_performance_level(self, obj) -> str | None:
        return self._summary(obj)["performance_level"]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_completion_warning(self, obj) -> str | None:
        return self._summary(obj)["completion_warning"]
