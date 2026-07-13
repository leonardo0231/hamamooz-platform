from __future__ import annotations

from rest_framework import serializers

from apps.organizations.models import Organization, School
from apps.organizations.selectors import accessible_organizations


class OrganizationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "code",
        )
        read_only_fields = fields


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "code",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class SchoolSerializer(serializers.ModelSerializer):
    organization = OrganizationSummarySerializer(
        read_only=True,
    )

    organization_id = serializers.PrimaryKeyRelatedField(
        source="organization",
        queryset=Organization.objects.none(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = School
        fields = (
            "id",
            "organization",
            "organization_id",
            "name",
            "code",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
        )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if request is None or not request.user.is_authenticated:
            return

        self.fields["organization_id"].queryset = accessible_organizations(
            request.user,
        )

    def validate(self, attrs: dict) -> dict:
        organization = attrs.get("organization")

        if self.instance is None and organization is None:
            raise serializers.ValidationError(
                {
                    "organization_id": (
                        "This field is required when creating a school."
                    )
                }
            )

        if (
            self.instance is not None
            and organization is not None
            and organization != self.instance.organization
        ):
            raise serializers.ValidationError(
                {
                    "organization_id": (
                        "Moving a school to another organization is not allowed."
                    )
                }
            )

        return attrs
