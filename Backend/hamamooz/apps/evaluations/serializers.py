from collections import defaultdict

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .catalog import DOMAIN_DEFINITIONS, METRIC_CATALOG
from .models import MetricScore, MonthlyEvaluation


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
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _domain_values(self, obj):
        grouped = defaultdict(list)
        for score in obj.metric_scores.all():
            definition = METRIC_CATALOG[score.metric_code]
            grouped[definition["domain_code"]].append(score.value)
        return grouped

    @extend_schema_field(DomainScoreSerializer(many=True))
    def get_domain_scores(self, obj) -> list[dict]:
        grouped = self._domain_values(obj)
        return [
            {
                "code": code,
                "title": title,
                "weight": weight,
                "score": round(sum(grouped[code]) / len(grouped[code]) * 4, 2)
                if grouped[code]
                else None,
                "completed_metrics": len(grouped[code]),
            }
            for code, (title, weight) in DOMAIN_DEFINITIONS.items()
        ]

    @extend_schema_field(serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True))
    def get_overall_score(self, obj) -> float | None:
        domains = [item for item in self.get_domain_scores(obj) if item["score"] is not None]
        if not domains:
            return None
        total_weight = sum(item["weight"] for item in domains)
        return round(
            sum(item["score"] * item["weight"] for item in domains) / total_weight,
            2,
        )

    @extend_schema_field(serializers.DecimalField(max_digits=5, decimal_places=2))
    def get_completion_percent(self, obj) -> float:
        return round(obj.metric_scores.count() / len(METRIC_CATALOG) * 100, 2)
