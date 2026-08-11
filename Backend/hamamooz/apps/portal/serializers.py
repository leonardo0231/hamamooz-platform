from rest_framework import serializers

from hamamooz.apps.accounts.access import accessible_organization_ids

from .models import PortalVisibilityPolicy


class PortalStudentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    status = serializers.CharField()


class PortalReportSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    report_type = serializers.CharField()
    output_format = serializers.ChoiceField(choices=["pdf", "docx"])
    term = serializers.CharField()
    created_at = serializers.DateTimeField()
    released_at = serializers.DateTimeField()


class PortalRecommendationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    priority = serializers.CharField()
    approved_text = serializers.CharField()
    approved_at = serializers.DateTimeField()


class PortalGuidePlanSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    objectives = serializers.CharField()
    released_at = serializers.DateTimeField()


class PortalAttendanceSerializer(serializers.Serializer):
    finalized_session_count = serializers.IntegerField()
    unexcused_absence_count = serializers.IntegerField()
    excused_absence_count = serializers.IntegerField()


class PortalChildrenResponseSerializer(serializers.Serializer):
    children = PortalStudentSerializer(many=True)


class PortalReportsResponseSerializer(serializers.Serializer):
    reports = PortalReportSerializer(many=True)


class PortalRecommendationsResponseSerializer(serializers.Serializer):
    recommendations = PortalRecommendationSerializer(many=True)


class PortalGuidePlansResponseSerializer(serializers.Serializer):
    guide_plans = PortalGuidePlanSerializer(many=True)


class PortalVisibilityPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalVisibilityPolicy
        fields = ["id", "organization", "resource", "visibility", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_organization(self, organization):
        if organization.id not in set(accessible_organization_ids(self.context["request"].user)):
            raise serializers.ValidationError("Organization is outside your access scope.")
        return organization

    def validate(self, attrs):
        resource = attrs.get("resource") or self.instance.resource
        visibility = attrs.get("visibility") or self.instance.visibility
        if (
            resource == PortalVisibilityPolicy.Resource.COUNSELING
            and visibility != PortalVisibilityPolicy.Visibility.NEVER
        ):
            raise serializers.ValidationError(
                {"visibility": "Counseling is never visible through a portal."}
            )
        return attrs
