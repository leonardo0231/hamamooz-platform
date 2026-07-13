from __future__ import annotations

from rest_framework import serializers

from apps.accounts.api.serializers import (
    UserSerializer,
)
from apps.accounts.models import User
from apps.organizations.models import (
    Organization,
    RoleAssignment,
    School,
    SchoolMembership,
)
from apps.organizations.selectors import (
    accessible_organizations,
    manageable_schools,
)
from apps.permissions.models import SystemRole


class OrganizationSummarySerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = Organization

        fields = (
            "id",
            "name",
            "code",
        )

        read_only_fields = fields


class SchoolSummarySerializer(
    serializers.ModelSerializer
):
    organization = OrganizationSummarySerializer(
        read_only=True
    )

    class Meta:
        model = School

        fields = (
            "id",
            "name",
            "code",
            "organization",
            "is_active",
        )

        read_only_fields = fields


class OrganizationSerializer(
    serializers.ModelSerializer
):
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


class SchoolSerializer(
    serializers.ModelSerializer
):
    organization = OrganizationSummarySerializer(
        read_only=True
    )

    organization_id = (
        serializers.PrimaryKeyRelatedField(
            source="organization",
            queryset=Organization.objects.none(),
            write_only=True,
            required=False,
        )
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

        if (
            request is None
            or not request.user.is_authenticated
        ):
            return

        self.fields[
            "organization_id"
        ].queryset = accessible_organizations(
            request.user
        )

    def validate(self, attrs: dict) -> dict:
        organization = attrs.get("organization")

        if (
            self.instance is None
            and organization is None
        ):
            raise serializers.ValidationError(
                {
                    "organization_id": (
                        "This field is required when "
                        "creating a school."
                    )
                }
            )

        if (
            self.instance is not None
            and organization is not None
            and organization
            != self.instance.organization
        ):
            raise serializers.ValidationError(
                {
                    "organization_id": (
                        "Moving a school to another "
                        "organization is not allowed."
                    )
                }
            )

        return attrs


class RoleAssignmentSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = RoleAssignment

        fields = (
            "id",
            "role",
            "is_active",
            "granted_at",
            "granted_by",
            "revoked_at",
            "revoked_by",
            "revocation_reason",
        )

        read_only_fields = fields


class SchoolMembershipSerializer(
    serializers.ModelSerializer
):
    user = UserSerializer(read_only=True)

    school = SchoolSummarySerializer(
        read_only=True
    )

    roles = RoleAssignmentSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = SchoolMembership

        fields = (
            "id",
            "user",
            "school",
            "is_active",
            "created_at",
            "updated_at",
            "deactivated_at",
            "deactivated_by",
            "deactivation_reason",
            "roles",
        )

        read_only_fields = fields


class SchoolMembershipCreateSerializer(
    serializers.Serializer
):
    user_id = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.filter(
            is_active=True
        ),
    )

    school_id = serializers.PrimaryKeyRelatedField(
        source="school",
        queryset=School.objects.none(),
    )

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if (
            request is None
            or not request.user.is_authenticated
        ):
            return

        self.fields[
            "school_id"
        ].queryset = manageable_schools(
            request.user
        )


class MembershipActivateSerializer(
    serializers.Serializer
):
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )


class MembershipDeactivateSerializer(
    serializers.Serializer
):
    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        min_length=3,
        max_length=1000,
        trim_whitespace=True,
    )


class RoleGrantSerializer(
    serializers.Serializer
):
    role = serializers.ChoiceField(
        choices=SystemRole.choices,
    )

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )


class RoleRevokeSerializer(
    serializers.Serializer
):
    role = serializers.ChoiceField(
        choices=SystemRole.choices,
    )

    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        min_length=3,
        max_length=1000,
        trim_whitespace=True,
    )