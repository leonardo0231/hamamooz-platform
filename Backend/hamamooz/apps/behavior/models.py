from hashlib import sha256
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel


def behavior_attachment_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return (
        f"behavior/{instance.event.organization_id}/{instance.event.school_id}/"
        f"{instance.event_id}/{instance.id}{suffix}"
    )


class BehaviorEventType(SoftDeleteModel):
    class Polarity(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEGATIVE = "negative", "Negative"
        NEUTRAL = "neutral", "Neutral"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="behavior_event_types"
    )
    code = models.CharField(max_length=50)
    title = models.CharField(max_length=150)
    default_polarity = models.CharField(max_length=10, choices=Polarity.choices)
    default_severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.LOW
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["organization", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                condition=models.Q(is_deleted=False),
                name="uq_behavior_event_type_org_code",
            )
        ]
        indexes = [models.Index(fields=["organization", "is_active", "code"])]


class BehaviorEvent(SoftDeleteModel):
    class Polarity(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEGATIVE = "negative", "Negative"
        NEUTRAL = "neutral", "Neutral"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"
        UNDER_FOLLOW_UP = "under_follow_up", "Under follow-up"
        RESOLVED = "resolved", "Resolved"
        VOIDED = "voided", "Voided"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="behavior_events"
    )
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="behavior_events"
    )
    academic_year = models.ForeignKey(
        "organizations.AcademicYear", on_delete=models.PROTECT, related_name="behavior_events"
    )
    enrollment = models.ForeignKey(
        "students.Enrollment", on_delete=models.PROTECT, related_name="behavior_events"
    )
    event_type = models.ForeignKey(
        BehaviorEventType, on_delete=models.PROTECT, related_name="events"
    )
    polarity = models.CharField(max_length=10, choices=Polarity.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices)
    occurred_at = models.DateTimeField(db_index=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_behavior_events"
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="confirmed_behavior_events",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="voided_behavior_events",
    )
    void_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status__in=["draft", "voided"]) | models.Q(confirmed_at__isnull=False)
                ),
                name="ck_behavior_event_confirmed_timestamp",
            )
        ]
        indexes = [
            models.Index(fields=["school", "academic_year", "enrollment", "status"]),
            models.Index(fields=["school", "occurred_at", "severity"]),
        ]

    def clean(self):
        errors = {}
        if (
            self.school_id
            and self.organization_id
            and self.school.organization_id != self.organization_id
        ):
            errors["school"] = "School must belong to the event organization."
        if (
            self.academic_year_id
            and self.organization_id
            and self.academic_year.organization_id != self.organization_id
        ):
            errors["academic_year"] = "Academic year must belong to the event organization."
        if self.enrollment_id:
            if self.school_id and self.enrollment.school_id != self.school_id:
                errors["enrollment"] = "Enrollment must belong to the event school."
            if self.academic_year_id and self.enrollment.academic_year_id != self.academic_year_id:
                errors["enrollment"] = "Enrollment must belong to the event academic year."
        if (
            self.event_type_id
            and self.organization_id
            and self.event_type.organization_id != self.organization_id
        ):
            errors["event_type"] = "Event type must belong to the event organization."
        if self.status == self.Status.VOIDED and not self.void_reason:
            errors["void_reason"] = "A voided event requires a reason."
        if errors:
            raise ValidationError(errors)


class BehaviorAction(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    event = models.ForeignKey(BehaviorEvent, on_delete=models.PROTECT, related_name="actions")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="behavior_actions",
    )
    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "due_at", "created_at"]
        indexes = [models.Index(fields=["event", "status", "due_at"])]

    @property
    def organization_id(self):
        return self.event.organization_id

    @property
    def school_id(self):
        return self.event.school_id


class BehaviorFollowUp(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    event = models.ForeignKey(BehaviorEvent, on_delete=models.PROTECT, related_name="follow_ups")
    due_at = models.DateTimeField()
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="completed_behavior_follow_ups",
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "due_at"]
        indexes = [models.Index(fields=["event", "status", "due_at"])]

    @property
    def organization_id(self):
        return self.event.organization_id

    @property
    def school_id(self):
        return self.event.school_id


class BehaviorAttachment(TimeStampedUUIDModel):
    event = models.ForeignKey(BehaviorEvent, on_delete=models.PROTECT, related_name="attachments")
    file = models.FileField(upload_to=behavior_attachment_upload_to)
    original_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="behavior_attachments"
    )

    @property
    def organization_id(self):
        return self.event.organization_id

    @property
    def school_id(self):
        return self.event.school_id


class BehaviorEventRevision(TimeStampedUUIDModel):
    event = models.ForeignKey(BehaviorEvent, on_delete=models.PROTECT, related_name="revisions")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="behavior_event_revisions"
    )
    reason = models.CharField(max_length=500)
    changed_fields = models.JSONField(default=list)
    previous_occurred_at = models.DateTimeField(null=True, blank=True)
    previous_description_digest = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event", "-created_at"])]

    @staticmethod
    def description_digest(value):
        return sha256(value.encode("utf-8")).hexdigest()

    @property
    def organization_id(self):
        return self.event.organization_id

    @property
    def school_id(self):
        return self.event.school_id
