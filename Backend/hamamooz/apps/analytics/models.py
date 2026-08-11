from django.conf import settings
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel


class AnalyticsRuleConfig(SoftDeleteModel):
    """Organization parameters for an algorithm that remains versioned in code."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="analytics_rule_configs",
    )
    rule_code = models.CharField(max_length=100)
    rule_version = models.PositiveSmallIntegerField()
    enabled = models.BooleanField(default=True)
    parameters = models.JSONField(default=dict, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["organization", "rule_code", "-rule_version"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "rule_code", "rule_version"],
                condition=models.Q(is_deleted=False),
                name="uq_analytics_rule_config_org_code_version",
            ),
            models.CheckConstraint(
                condition=models.Q(effective_to__isnull=True)
                | models.Q(effective_from__isnull=True)
                | models.Q(effective_to__gte=models.F("effective_from")),
                name="ck_analytics_rule_config_effective_range",
            ),
        ]
        indexes = [models.Index(fields=["organization", "enabled", "rule_code"])]


class AnalyticsRun(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class Trigger(models.TextChoices):
        MANUAL = "manual", "Manual"
        DATA_MUTATION = "data_mutation", "Data mutation"
        RECONCILIATION = "reconciliation", "Reconciliation"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="analytics_runs"
    )
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="analytics_runs"
    )
    enrollment = models.ForeignKey(
        "students.Enrollment", on_delete=models.PROTECT, related_name="analytics_runs"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    trigger = models.CharField(max_length=30, choices=Trigger.choices, default=Trigger.MANUAL)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="requested_analytics_runs",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=100, blank=True)
    rule_snapshot = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["enrollment", "-created_at"]),
            models.Index(fields=["school", "status", "-created_at"]),
        ]

    def clean(self):
        if (
            self.school_id
            and self.organization_id
            and self.school.organization_id != self.organization_id
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError({"school": "School must belong to the analytics organization."})
        if self.enrollment_id and self.school_id and self.enrollment.school_id != self.school_id:
            from django.core.exceptions import ValidationError

            raise ValidationError({"enrollment": "Enrollment must belong to the analytics school."})


class StudentRiskSignal(TimeStampedUUIDModel):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        SUPERSEDED = "superseded", "Superseded"
        RESOLVED = "resolved", "Resolved"

    run = models.ForeignKey(AnalyticsRun, on_delete=models.PROTECT, related_name="signals")
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="risk_signals"
    )
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="risk_signals"
    )
    enrollment = models.ForeignKey(
        "students.Enrollment", on_delete=models.PROTECT, related_name="risk_signals"
    )
    rule_code = models.CharField(max_length=100)
    rule_version = models.PositiveSmallIntegerField()
    severity = models.CharField(max_length=20, choices=Severity.choices)
    evidence = models.JSONField(default=dict)
    explanation = models.CharField(max_length=1000)
    window = models.JSONField(default=dict)
    state = models.CharField(max_length=20, choices=State.choices, default=State.ACTIVE)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "enrollment", "rule_code", "rule_version"],
                name="uq_signal_per_run_enrollment_rule_version",
            )
        ]
        indexes = [
            models.Index(fields=["school", "state", "severity"]),
            models.Index(fields=["enrollment", "state", "-created_at"]),
            models.Index(fields=["rule_code", "rule_version", "state"]),
        ]


class OperationalAlert(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        CLOSED = "closed", "Closed"

    signal = models.OneToOneField(
        StudentRiskSignal, on_delete=models.PROTECT, related_name="operational_alert"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="acknowledged_operational_alerts",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    @property
    def organization_id(self):
        return self.signal.organization_id

    @property
    def school_id(self):
        return self.signal.school_id
