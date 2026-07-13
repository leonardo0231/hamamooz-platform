from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.permissions.models import SystemRole


class Organization(models.Model):
    name = models.CharField(max_length=200)

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["name"]

    def __str__(self) -> str:
        return self.name


class School(models.Model):
    organization = models.ForeignKey(
        Organization,
        related_name="schools",
        on_delete=models.PROTECT,
    )

    name = models.CharField(max_length=200)

    code = models.CharField(max_length=50)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("organization", "code"),
                name="unique_school_code_per_org",
            ),
        )

    def __str__(self) -> str:
        return self.name


class SchoolMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="school_memberships",
        on_delete=models.PROTECT,
    )

    school = models.ForeignKey(
        School,
        related_name="memberships",
        on_delete=models.PROTECT,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    deactivated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    deactivated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="deactivated_school_memberships",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    deactivation_reason = models.TextField(blank=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("user", "school"),
                name="unique_user_school_membership",
            ),
        )

    def __str__(self) -> str:
        return f"{self.user} @ {self.school}"


class RoleAssignment(models.Model):
    membership = models.ForeignKey(
        SchoolMembership,
        related_name="roles",
        on_delete=models.PROTECT,
    )

    role = models.CharField(
        max_length=50,
        choices=SystemRole.choices,
    )

    is_active = models.BooleanField(default=True)

    granted_at = models.DateTimeField(default=timezone.now)

    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="granted_role_assignments",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="revoked_role_assignments",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    revocation_reason = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("membership", "role"),
                name="unique_role_assignment",
            ),
        )

    def __str__(self) -> str:
        return f"{self.membership} — {self.get_role_display()}"


class AccessAuditEvent(models.Model):
    class Action(models.TextChoices):
        MEMBERSHIP_ACTIVATED = (
            "MEMBERSHIP_ACTIVATED",
            "عضویت فعال شد",
        )

        MEMBERSHIP_DEACTIVATED = (
            "MEMBERSHIP_DEACTIVATED",
            "عضویت غیرفعال شد",
        )

        ROLE_GRANTED = (
            "ROLE_GRANTED",
            "نقش اعطا شد",
        )

        ROLE_REVOKED = (
            "ROLE_REVOKED",
            "نقش لغو شد",
        )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="access_events_performed",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="access_events_received",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    organization = models.ForeignKey(
        Organization,
        related_name="access_audit_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    school = models.ForeignKey(
        School,
        related_name="access_audit_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    membership = models.ForeignKey(
        SchoolMembership,
        related_name="audit_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    action = models.CharField(
        max_length=40,
        choices=Action.choices,
    )

    role = models.CharField(
        max_length=50,
        blank=True,
    )

    reason = models.TextField(blank=True)

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar[list[str]] = [
            "-created_at",
            "-id",
        ]

        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["action", "created_at"],
                name="access_evt_action_time_idx",
            ),
            models.Index(
                fields=["target_user", "created_at"],
                name="access_evt_target_time_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.action} at {self.created_at.isoformat()}"