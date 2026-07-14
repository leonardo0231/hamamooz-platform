from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import LoginAttempt, User
from apps.core.admin import (
    NoHardDeleteAdminMixin,
    SuperuserOnlyAdminMixin,
    SuperuserReadOnlyAdminMixin,
)


@admin.register(User)
class UserAdmin(
    SuperuserOnlyAdminMixin,
    NoHardDeleteAdminMixin,
    DjangoUserAdmin,
):
    ordering = ("email",)

    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "password",
                )
            },
        ),
        (
            "Personal information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    readonly_fields = (
        "last_login",
        "date_joined",
    )


@admin.register(LoginAttempt)
class LoginAttemptAdmin(
    SuperuserReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "identifier_hash",
        "ip_address",
        "succeeded",
        "created_at",
    )

    list_filter = (
        "succeeded",
        "created_at",
    )

    search_fields = (
        "identifier_hash",
        "ip_address",
    )

    date_hierarchy = "created_at"