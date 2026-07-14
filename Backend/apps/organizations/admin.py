from django.contrib import admin

from apps.core.admin import (
    NoHardDeleteAdminMixin,
    SuperuserOnlyAdminMixin,
    SuperuserReadOnlyAdminMixin,
)
from apps.organizations.models import (
    AccessAuditEvent,
    Organization,
    RoleAssignment,
    School,
    SchoolMembership,
)


@admin.register(Organization)
class OrganizationAdmin(
    SuperuserOnlyAdminMixin,
    NoHardDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "code",
        "is_active",
        "created_at",
    )

    list_filter = ("is_active",)

    search_fields = (
        "name",
        "code",
    )


@admin.register(School)
class SchoolAdmin(
    SuperuserOnlyAdminMixin,
    NoHardDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "organization",
        "code",
        "is_active",
    )

    list_filter = (
        "is_active",
        "organization",
    )

    search_fields = (
        "name",
        "code",
        "organization__name",
    )

    list_select_related = ("organization",)


@admin.register(SchoolMembership)
class SchoolMembershipAdmin(
    SuperuserReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "user",
        "school",
        "is_active",
        "created_at",
        "deactivated_at",
    )

    list_filter = (
        "is_active",
        "school__organization",
        "school",
    )

    search_fields = (
        "user__email",
        "school__name",
    )

    list_select_related = (
        "user",
        "school",
        "school__organization",
    )


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(
    SuperuserReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "membership",
        "role",
        "is_active",
        "granted_at",
        "revoked_at",
    )

    list_filter = (
        "role",
        "is_active",
    )

    search_fields = (
        "membership__user__email",
        "membership__school__name",
    )

    list_select_related = (
        "membership",
        "membership__user",
        "membership__school",
    )


@admin.register(AccessAuditEvent)
class AccessAuditEventAdmin(
    SuperuserReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "action",
        "target_user",
        "school",
        "role",
        "actor",
        "created_at",
    )

    list_filter = (
        "action",
        "role",
        "created_at",
    )

    search_fields = (
        "target_user__email",
        "actor__email",
        "school__name",
        "reason",
    )

    list_select_related = (
        "actor",
        "target_user",
        "organization",
        "school",
        "membership",
    )

    date_hierarchy = "created_at"