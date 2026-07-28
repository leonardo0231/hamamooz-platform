from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel


class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    national_id = models.CharField(max_length=10, unique=True, null=True, blank=True)
    must_change_password = models.BooleanField(default=False)

    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.get_full_name() or self.username


class Role(models.TextChoices):
    SYSTEM_ADMIN = "system_admin", "مدیر کل سامانه"
    ORGANIZATION_ADMIN = "organization_admin", "مدیر مجموعه"
    SCHOOL_MANAGER = "school_manager", "مدیر شعبه"
    EDUCATIONAL_DEPUTY = "educational_deputy", "معاون آموزشی"
    OPERATOR = "operator", "اپراتور"
    TEACHER = "teacher", "دبیر"


class RoleAssignment(SoftDeleteModel):
    GLOBAL_ROLES = {Role.SYSTEM_ADMIN, Role.ORGANIZATION_ADMIN}

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="role_assignments")
    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )
    school = models.ForeignKey(
        "organizations.School",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )
    role = models.CharField(max_length=40, choices=Role.choices, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["user", "organization", "school", "role"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                condition=models.Q(
                    organization__isnull=True,
                    school__isnull=True,
                    is_deleted=False,
                ),
                name="uq_user_role_global_scope",
            ),
            models.UniqueConstraint(
                fields=["user", "organization", "role"],
                condition=models.Q(
                    organization__isnull=False,
                    school__isnull=True,
                    is_deleted=False,
                ),
                name="uq_user_role_org_scope",
            ),
            models.UniqueConstraint(
                fields=["user", "school", "role"],
                condition=models.Q(school__isnull=False, is_deleted=False),
                name="uq_user_role_school_scope",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_active", "role"]),
            models.Index(fields=["school", "is_active", "role"]),
        ]

    def clean(self):
        errors = {}
        if self.role == Role.SYSTEM_ADMIN:
            if self.organization_id or self.school_id:
                errors["role"] = "مدیر کل باید بدون مجموعه و شعبه تعریف شود."
        elif self.role == Role.ORGANIZATION_ADMIN:
            if not self.organization_id or self.school_id:
                errors["role"] = "مدیر مجموعه باید برای یک مجموعه و بدون شعبه تعریف شود."
        elif not self.organization_id or not self.school_id:
            errors["role"] = "این نقش باید به مجموعه و شعبه متصل باشد."
        if (
            self.school_id
            and self.organization_id
            and self.school.organization_id != self.organization_id
        ):
            errors["school"] = "شعبه متعلق به مجموعه انتخاب‌شده نیست."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.user} - {self.get_role_display()}"
