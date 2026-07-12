from django.contrib import admin

from .models import (
    Organization,
    School,
    SchoolMembership,
    RoleAssignment,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):

    list_display = [
        "name",
        "code",
        "is_active",
    ]



@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):

    list_display = [
        "name",
        "organization",
        "is_active",
    ]



admin.site.register(
    SchoolMembership
)


admin.site.register(
    RoleAssignment
)