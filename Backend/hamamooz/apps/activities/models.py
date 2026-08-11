from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel


def activity_attachment_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return (
        f"activities/{instance.activity.organization_id}/{instance.activity.school_id}/"
        f"{instance.activity_id}/{instance.id}{suffix}"
    )


class Activity(SoftDeleteModel):
    class Kind(models.TextChoices):
        CULTURAL = "cultural", "Cultural"
        COMPETITION = "competition", "Competition"
        RESEARCH = "research", "Research"
        SPORT = "sport", "Sport"
        ART = "art", "Art"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="activities"
    )
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="activities"
    )
    academic_year = models.ForeignKey(
        "organizations.AcademicYear", on_delete=models.PROTECT, related_name="activities"
    )
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_activities"
    )

    class Meta:
        ordering = ["-starts_at", "title"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__isnull=True)
                | models.Q(ends_at__gte=models.F("starts_at")),
                name="ck_activity_end_after_start",
            )
        ]
        indexes = [
            models.Index(fields=["school", "academic_year", "kind", "status"]),
            models.Index(fields=["school", "starts_at"]),
        ]

    def clean(self):
        errors = {}
        if (
            self.school_id
            and self.organization_id
            and self.school.organization_id != self.organization_id
        ):
            errors["school"] = "School must belong to the activity organization."
        if (
            self.academic_year_id
            and self.organization_id
            and self.academic_year.organization_id != self.organization_id
        ):
            errors["academic_year"] = "Academic year must belong to the activity organization."
        if self.ends_at and self.starts_at and self.ends_at < self.starts_at:
            errors["ends_at"] = "An activity cannot end before it starts."
        if errors:
            raise ValidationError(errors)


class ActivityParticipation(SoftDeleteModel):
    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        REGISTERED = "registered", "Registered"
        PARTICIPATED = "participated", "Participated"
        WITHDRAWN = "withdrawn", "Withdrawn"
        ABSENT = "absent", "Absent"

    activity = models.ForeignKey(Activity, on_delete=models.PROTECT, related_name="participations")
    enrollment = models.ForeignKey(
        "students.Enrollment", on_delete=models.PROTECT, related_name="activity_participations"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INVITED)
    participation_role = models.CharField(max_length=100, blank=True)
    result = models.CharField(max_length=250, blank=True)
    placement = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["activity", "enrollment"]
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "enrollment"],
                condition=models.Q(is_deleted=False),
                name="uq_activity_participation_active",
            )
        ]
        indexes = [
            models.Index(fields=["activity", "status"]),
            models.Index(fields=["enrollment", "status"]),
        ]

    def clean(self):
        if self.activity_id and self.enrollment_id:
            errors = {}
            if self.activity.school_id != self.enrollment.school_id:
                errors["enrollment"] = (
                    "Participation enrollment must belong to the activity school."
                )
            if self.activity.academic_year_id != self.enrollment.academic_year_id:
                errors["enrollment"] = "Participation enrollment must belong to the activity year."
            if errors:
                raise ValidationError(errors)

    @property
    def organization_id(self):
        return self.activity.organization_id

    @property
    def school_id(self):
        return self.activity.school_id


class ActivityAchievement(TimeStampedUUIDModel):
    participation = models.ForeignKey(
        ActivityParticipation, on_delete=models.PROTECT, related_name="achievements"
    )
    title = models.CharField(max_length=200)
    result = models.CharField(max_length=250, blank=True)
    placement = models.PositiveSmallIntegerField(null=True, blank=True)
    awarded_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-awarded_at", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["participation", "title"],
                name="uq_activity_achievement_participation_title",
            )
        ]

    @property
    def organization_id(self):
        return self.participation.organization_id

    @property
    def school_id(self):
        return self.participation.school_id


class ActivityAttachment(TimeStampedUUIDModel):
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT, related_name="attachments")
    file = models.FileField(upload_to=activity_attachment_upload_to)
    original_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="activity_attachments"
    )

    @property
    def organization_id(self):
        return self.activity.organization_id

    @property
    def school_id(self):
        return self.activity.school_id
