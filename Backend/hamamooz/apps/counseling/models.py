from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel


def counseling_attachment_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return (
        f"counseling/{instance.case.organization_id}/{instance.case.school_id}/"
        f"{instance.case_id}/{instance.id}{suffix}"
    )


class CounselingCase(SoftDeleteModel):
    """A counselor-owned case.  It intentionally contains no session narrative."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"

    class RiskLevel(models.TextChoices):
        NONE = "none", "None"
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="counseling_cases"
    )
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="counseling_cases"
    )
    enrollment = models.ForeignKey(
        "students.Enrollment", on_delete=models.PROTECT, related_name="counseling_cases"
    )
    assigned_counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_counseling_cases"
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="opened_counseling_cases"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    shared_risk_level = models.CharField(
        max_length=20, choices=RiskLevel.choices, default=RiskLevel.NONE
    )
    shared_follow_up_status = models.CharField(max_length=120, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["draft", "active"])
                | models.Q(closed_at__isnull=False),
                name="ck_counseling_case_closed_timestamp",
            )
        ]
        indexes = [
            models.Index(fields=["school", "status", "shared_risk_level"]),
            models.Index(fields=["assigned_counselor", "status"]),
            models.Index(fields=["enrollment", "status"]),
        ]

    def clean(self):
        errors = {}
        if (
            self.school_id
            and self.organization_id
            and self.school.organization_id != self.organization_id
        ):
            errors["school"] = "School must belong to the case organization."
        if self.enrollment_id:
            if self.school_id and self.enrollment.school_id != self.school_id:
                errors["enrollment"] = "Enrollment must belong to the case school."
            if (
                self.organization_id
                and self.enrollment.school.organization_id != self.organization_id
            ):
                errors["enrollment"] = "Enrollment must belong to the case organization."
        if errors:
            raise ValidationError(errors)


class CounselingSession(TimeStampedUUIDModel):
    """Immutable private clinical note. Never serialize it in a shared case response."""

    case = models.ForeignKey(CounselingCase, on_delete=models.PROTECT, related_name="sessions")
    occurred_at = models.DateTimeField()
    private_note = models.TextField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_counseling_sessions",
    )

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        indexes = [models.Index(fields=["case", "-occurred_at"])]

    @property
    def organization_id(self):
        return self.case.organization_id

    @property
    def school_id(self):
        return self.case.school_id


class CounselingFollowUp(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    case = models.ForeignKey(CounselingCase, on_delete=models.PROTECT, related_name="follow_ups")
    title = models.CharField(max_length=200)
    due_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    shared_note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_counseling_follow_ups",
    )

    class Meta:
        ordering = ["status", "due_at", "created_at"]
        indexes = [models.Index(fields=["case", "status", "due_at"])]

    @property
    def organization_id(self):
        return self.case.organization_id

    @property
    def school_id(self):
        return self.case.school_id


class CounselingActionPlan(TimeStampedUUIDModel):
    class Visibility(models.TextChoices):
        SHARED = "shared", "Shared staff"
        RELEASED = "released", "Released"

    case = models.ForeignKey(CounselingCase, on_delete=models.PROTECT, related_name="action_plans")
    title = models.CharField(max_length=200)
    guidance = models.TextField()
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.SHARED
    )
    released_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_counseling_action_plans",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(visibility="shared") | models.Q(released_at__isnull=False),
                name="ck_counseling_released_action_plan_timestamp",
            )
        ]
        indexes = [models.Index(fields=["case", "visibility"])]

    @property
    def organization_id(self):
        return self.case.organization_id

    @property
    def school_id(self):
        return self.case.school_id


class Referral(TimeStampedUUIDModel):
    """An explicit hand-off; accepting it creates a fresh case without session notes."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    source_case = models.ForeignKey(
        CounselingCase, on_delete=models.PROTECT, related_name="referrals"
    )
    target_enrollment = models.ForeignKey(
        "students.Enrollment",
        on_delete=models.PROTECT,
        related_name="incoming_counseling_referrals",
    )
    target_counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="incoming_counseling_referrals",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_counseling_referrals",
    )
    purpose = models.CharField(max_length=500)
    handoff_summary = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    accepted_case = models.OneToOneField(
        CounselingCase,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="accepted_from_referral",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target_counselor", "status"]),
            models.Index(fields=["source_case", "status"]),
        ]

    def clean(self):
        if (
            self.source_case_id
            and self.target_enrollment_id
            and self.target_enrollment.student_id != self.source_case.enrollment.student_id
        ):
            raise ValidationError({"target_enrollment": "A referral must target the same student."})


class CounselingAttachment(TimeStampedUUIDModel):
    case = models.ForeignKey(CounselingCase, on_delete=models.PROTECT, related_name="attachments")
    file = models.FileField(upload_to=counseling_attachment_upload_to)
    original_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="counseling_attachments"
    )

    @property
    def organization_id(self):
        return self.case.organization_id

    @property
    def school_id(self):
        return self.case.school_id
