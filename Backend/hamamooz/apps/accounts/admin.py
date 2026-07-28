from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import RoleAssignment, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("اطلاعات هم‌آموز", {"fields": ("phone", "national_id", "must_change_password")}),
    )


admin.site.register(RoleAssignment)
