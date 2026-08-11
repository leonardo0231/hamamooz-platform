from rest_framework import serializers

from hamamooz.apps.accounts.access import (
    accessible_organization_ids,
    allowed_class_ids_for_roles,
    selected_school_ids,
)
from hamamooz.apps.accounts.models import Role

from .models import AnalyticsRuleConfig, AnalyticsRun, OperationalAlert, StudentRiskSignal


class AnalyticsRuleConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsRuleConfig
        fields = [
            "id",
            "organization",
            "rule_code",
            "rule_version",
            "enabled",
            "parameters",
            "effective_from",
            "effective_to",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_organization(self, value):
        if value.id not in set(accessible_organization_ids(self.context["request"].user)):
            raise serializers.ValidationError("Organization is outside your access scope.")
        return value


class AnalyticsRunCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsRun
        fields = ["enrollment", "trigger"]

    def validate_enrollment(self, enrollment):
        request = self.context["request"]
        schools = selected_school_ids(request)
        classes = allowed_class_ids_for_roles(request.user, schools, [Role.STUDENT_AFFAIRS_DEPUTY])
        if enrollment.school_id not in set(schools) or enrollment.class_section_id not in set(
            classes
        ):
            raise serializers.ValidationError("Enrollment is outside your analytics scope.")
        return enrollment


class AnalyticsRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsRun
        fields = [
            "id",
            "organization",
            "school",
            "enrollment",
            "status",
            "trigger",
            "requested_by",
            "started_at",
            "completed_at",
            "error_code",
            "rule_snapshot",
            "created_at",
        ]
        read_only_fields = fields


class StudentRiskSignalSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)

    class Meta:
        model = StudentRiskSignal
        fields = [
            "id",
            "run",
            "organization",
            "school",
            "enrollment",
            "student_name",
            "rule_code",
            "rule_version",
            "severity",
            "evidence",
            "explanation",
            "window",
            "state",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = fields


class OperationalAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationalAlert
        fields = [
            "id",
            "signal",
            "status",
            "acknowledged_by",
            "acknowledged_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "signal", "created_at", "updated_at"]
