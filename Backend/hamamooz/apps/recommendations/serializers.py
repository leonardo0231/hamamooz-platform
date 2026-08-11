from rest_framework import serializers

from .models import Recommendation, RecommendationDecision


class RecommendationDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationDecision
        fields = ["id", "actor", "from_status", "to_status", "created_at"]
        read_only_fields = fields


class RecommendationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)
    decisions = RecommendationDecisionSerializer(many=True, read_only=True)

    class Meta:
        model = Recommendation
        fields = [
            "id",
            "organization",
            "school",
            "enrollment",
            "student_name",
            "source_signal",
            "audience",
            "rule_code",
            "rule_version",
            "priority",
            "reason_snapshot",
            "generated_text",
            "approved_text",
            "status",
            "reviewer",
            "approved_at",
            "expires_at",
            "decisions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class GenerateRecommendationsSerializer(serializers.Serializer):
    signal = serializers.UUIDField()


class RecommendationTransitionSerializer(serializers.Serializer):
    target_status = serializers.ChoiceField(
        choices=[choice for choice, _ in Recommendation.Status.choices]
    )
    approved_text = serializers.CharField(required=False, allow_blank=False)
    rationale = serializers.CharField(required=False, allow_blank=True, max_length=500)
