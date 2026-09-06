from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel

from .catalog import FRAMEWORK_VERSION


class MonthlyEvaluation(SoftDeleteModel):
    """Legacy monthly evaluation model.

    Kept during the data migration window so existing installations can be
    migrated safely. New imports and report-card code must use
    AssessmentPeriod/Indicator/AssessmentRecord instead of month_no.
    """

    enrollment = models.ForeignKey(
        "students.Enrollment",
        on_delete=models.PROTECT,
        related_name="monthly_evaluations",
    )
    month_no = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    framework_version = models.CharField(max_length=20, default=FRAMEWORK_VERSION)
    note = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_monthly_evaluations",
    )
    source_import_job = models.ForeignKey(
        "imports.ImportJob",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="monthly_evaluations",
    )

    class Meta:
        ordering = ["-enrollment__academic_year__starts_on", "-month_no", "enrollment"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "month_no", "framework_version"],
                condition=models.Q(is_deleted=False),
                name="uq_monthly_evaluation_enrollment_month_version",
            ),
            models.CheckConstraint(
                condition=models.Q(month_no__gte=1, month_no__lte=12),
                name="ck_monthly_evaluation_month",
            ),
        ]
        indexes = [
            models.Index(fields=["enrollment", "month_no"]),
            models.Index(fields=["framework_version", "month_no"]),
        ]


class MetricScore(TimeStampedUUIDModel):
    """Legacy metric score storage paired with MonthlyEvaluation."""

    evaluation = models.ForeignKey(
        MonthlyEvaluation,
        on_delete=models.CASCADE,
        related_name="metric_scores",
    )
    metric_code = models.CharField(max_length=10)
    value = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    class Meta:
        ordering = ["metric_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["evaluation", "metric_code"],
                name="uq_evaluation_metric_code",
            ),
            models.CheckConstraint(
                condition=models.Q(value__gte=0, value__lte=5),
                name="ck_metric_score_value",
            ),
        ]
        indexes = [models.Index(fields=["metric_code", "value"])]


# Importing these models from the app's canonical models module is required for
# Django model discovery and for migrations to have a real model state.
from .dynamic_models import AssessmentPeriod, AssessmentRecord, Indicator  # noqa: E402,F401

__all__ = [
    "MonthlyEvaluation",
    "MetricScore",
    "AssessmentPeriod",
    "Indicator",
    "AssessmentRecord",
]
