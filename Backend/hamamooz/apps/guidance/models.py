from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel


class GuideTeacherAssignment(SoftDeleteModel):
    """A time-bounded guide-teacher relationship to a particular enrollment."""

    enrollment = models.ForeignKey(
        "students.Enrollment", on_delete=models.PROTECT, related_name="guide_teacher_assignments"
    )
    guide_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="guide_teacher_assignments"
    )
    starts_at = models.DateField()
    ends_at = models.DateField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_guide_teacher_assignments",
    )

    class Meta:
        ordering = ["enrollment", "-starts_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__isnull=True)
                | models.Q(ends_at__gte=models.F("starts_at")),
                name="ck_guidance_assignment_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["enrollment", "guide_teacher"],
                condition=models.Q(ends_at__isnull=True, is_deleted=False),
                name="uq_active_guide_assignment_per_teacher_enrollment",
            ),
        ]
        indexes = [
            models.Index(fields=["guide_teacher", "starts_at", "ends_at"]),
            models.Index(fields=["enrollment", "ends_at"]),
        ]

    def clean(self):
        if self.ends_at and self.starts_at and self.ends_at < self.starts_at:
            raise ValidationError({"ends_at": "An assignment cannot end before it starts."})

    @property
    def organization_id(self):
        return self.enrollment.school.organization_id

    @property
    def school_id(self):
        return self.enrollment.school_id


class GuideFollowUp(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    assignment = models.ForeignKey(
        GuideTeacherAssignment, on_delete=models.PROTECT, related_name="follow_ups"
    )
    title = models.CharField(max_length=200)
    due_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    note = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_guide_follow_ups"
    )

    class Meta:
        ordering = ["status", "due_at", "created_at"]
        indexes = [models.Index(fields=["assignment", "status", "due_at"])]

    @property
    def organization_id(self):
        return self.assignment.organization_id

    @property
    def school_id(self):
        return self.assignment.school_id


class GuideActionPlan(TimeStampedUUIDModel):
    class Visibility(models.TextChoices):
        STAFF = "staff", "Staff"
        RELEASED = "released", "Released"

    assignment = models.ForeignKey(
        GuideTeacherAssignment, on_delete=models.PROTECT, related_name="action_plans"
    )
    title = models.CharField(max_length=200)
    objectives = models.TextField()
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.STAFF
    )
    released_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_guide_action_plans",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(visibility="staff") | models.Q(released_at__isnull=False),
                name="ck_guidance_released_plan_timestamp",
            )
        ]
        indexes = [models.Index(fields=["assignment", "visibility"])]

    @property
    def organization_id(self):
        return self.assignment.organization_id

    @property
    def school_id(self):
        return self.assignment.school_id
