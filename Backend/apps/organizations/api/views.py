from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.organizations.api.exceptions import (
    OrganizationAccessDenied,
    SchoolAccessDenied,
)
from apps.organizations.api.permissions import (
    OrganizationAccessPermission,
    SchoolAccessPermission,
)
from apps.organizations.api.serializers import (
    OrganizationSerializer,
    SchoolSerializer,
)
from apps.organizations.selectors import (
    accessible_organizations,
    accessible_schools,
)
from apps.permissions.models import SystemRole
from apps.permissions.policies import (
    can_create_school_in_organization,
    has_role,
)


class OrganizationViewSet(ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = (
        IsAuthenticated,
        OrganizationAccessPermission,
    )

    http_method_names = (
        "get",
        "post",
        "patch",
        "head",
        "options",
    )

    search_fields = (
        "name",
        "code",
    )

    ordering_fields = (
        "name",
        "code",
        "created_at",
    )

    filterset_fields = (
        "is_active",
    )

    def get_queryset(self):
        return accessible_organizations(
            self.request.user,
        ).order_by("name")

    def perform_update(
        self,
        serializer: OrganizationSerializer,
    ) -> None:
        if not self.request.user.is_superuser:
            allowed_fields = {"name"}
            submitted_fields = set(serializer.validated_data)

            if submitted_fields - allowed_fields:
                raise OrganizationAccessDenied(
                    "Organization managers may only edit the organization name."
                )

        serializer.save()


class SchoolViewSet(ModelViewSet):
    serializer_class = SchoolSerializer
    permission_classes = (
        IsAuthenticated,
        SchoolAccessPermission,
    )

    http_method_names = (
        "get",
        "post",
        "patch",
        "head",
        "options",
    )

    search_fields = (
        "name",
        "code",
        "organization__name",
    )

    ordering_fields = (
        "name",
        "code",
        "created_at",
    )

    filterset_fields = (
        "organization",
        "is_active",
    )

    def get_queryset(self):
        return (
            accessible_schools(self.request.user)
            .select_related("organization")
            .order_by("organization__name", "name")
        )

    def perform_create(
        self,
        serializer: SchoolSerializer,
    ) -> None:
        organization = serializer.validated_data["organization"]

        if not can_create_school_in_organization(
            self.request.user,
            organization,
        ):
            raise SchoolAccessDenied(
                "Only system administrators and organization managers "
                "may create schools."
            )

        serializer.save()

    def perform_update(
        self,
        serializer: SchoolSerializer,
    ) -> None:
        school = serializer.instance
        user = self.request.user

        if user.is_superuser:
            serializer.save()
            return

        is_organization_manager = has_role(
            user,
            SystemRole.ORGANIZATION_MANAGER,
            organization=school.organization,
        )

        if is_organization_manager:
            allowed_fields = {
                "name",
                "code",
                "is_active",
            }
        else:
            allowed_fields = {
                "name",
                "code",
            }

        submitted_fields = set(serializer.validated_data)

        if submitted_fields - allowed_fields:
            raise SchoolAccessDenied(
                "You are not allowed to modify one or more submitted fields."
            )

        serializer.save()
