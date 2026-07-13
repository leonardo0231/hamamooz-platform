from django.contrib import admin

from apps.organizations.models import (
    Organization,
    RoleAssignment,
    School,
    SchoolMembership,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_active",
    )


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "is_active",
    )


admin.site.register((SchoolMembership, RoleAssignment))
