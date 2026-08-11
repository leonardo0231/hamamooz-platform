from django.conf import settings
from django.db import models

from hamamooz.apps.core.models import TimeStampedUUIDModel


class Recommendation(TimeStampedUUIDModel):
    class Audience(models.TextChoices):
        PARENT = "parent", "Parent"
        STUDENT = "student", "Student"
        GUIDE_TEACHER = "guide_teacher", "Guide teacher"
        TEACHER = "teacher", "Teacher"
        EDUCATIONAL_DEPUTY = "educational_deputy", "Educational deputy"
        COUNSELOR = "counselor", "Counselor"
        MANAGER = "manager", "Manager"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_REVIEW = "pending_review", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        DISMISSED = "dismissed", "Dismissed"
        EXPIRED = "expired", "Expired"
        SUPERSEDED = "superseded", "Superseded"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="recommendations"
    )
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="recommendations"
    )
    enrollment = models.ForeignKey(
        "students.Enrollment", on_delete=models.PROTECT, related_name="recommendations"
    )
    source_signal = models.ForeignKey(
        "analytics.StudentRiskSignal",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="recommendations",
    )
    audience = models.CharField(max_length=30, choices=Audience.choices)
    rule_code = models.CharField(max_length=100)
    rule_version = models.PositiveSmallIntegerField()
    priority = models.CharField(max_length=20, choices=Priority.choices)
    reason_snapshot = models.JSONField(default=dict)
    generated_text = models.TextField()
    approved_text = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reviewed_recommendations",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_signal", "audience", "rule_code", "rule_version"],
                condition=models.Q(status__in=["draft", "pending_review", "approved"]),
                name="uq_current_recommendation_per_signal_audience_rule",
            ),
            models.CheckConstraint(
                condition=models.Q(status="approved", approved_at__isnull=False)
                | ~models.Q(status="approved"),
                name="ck_recommendation_approved_timestamp",
            ),
        ]
        indexes = [
            models.Index(fields=["school", "status", "audience"]),
            models.Index(fields=["enrollment", "status", "-created_at"]),
            models.Index(fields=["rule_code", "rule_version"]),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if (
            self.school_id
            and self.organization_id
            and self.school.organization_id != self.organization_id
        ):
            errors["school"] = "School must belong to the recommendation organization."
        if self.enrollment_id and self.school_id and self.enrollment.school_id != self.school_id:
            errors["enrollment"] = "Enrollment must belong to the recommendation school."
        if (
            self.source_signal_id
            and self.enrollment_id
            and self.source_signal.enrollment_id != self.enrollment_id
        ):
            errors["source_signal"] = "Signal must belong to the recommendation enrollment."
        if self.status == self.Status.APPROVED and not self.approved_text:
            errors["approved_text"] = "An approved recommendation requires approved text."
        if errors:
            raise ValidationError(errors)


class RecommendationDecision(TimeStampedUUIDModel):
    recommendation = models.ForeignKey(
        Recommendation, on_delete=models.PROTECT, related_name="decisions"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recommendation_decisions"
    )
    from_status = models.CharField(max_length=30)
    to_status = models.CharField(max_length=30)
    rationale = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recommendation", "-created_at"])]

    @property
    def organization_id(self):
        return self.recommendation.organization_id

    @property
    def school_id(self):
        return self.recommendation.school_id
