from django.conf import settings
from django.db import models

from hamamooz.apps.core.models import TimeStampedUUIDModel


class AssessmentPeriod(TimeStampedUUIDModel):
    """Flexible assessment period replacing fixed month assumptions."""

    class PeriodType(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        SEASON = "season", "Season"
        EXAM = "exam", "Exam"
        CUSTOM = "custom", "Custom"

    title = models.CharField(max_length=100)
    period_type = models.CharField(
        max_length=20,
        choices=PeriodType.choices,
        default=PeriodType.CUSTOM,
    )
    academic_year = models.ForeignKey(
        "organizations.AcademicYear",
        on_delete=models.PROTECT,
        related_name="assessment_periods",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "title"],
                name="uq_assessment_period_title_year",
            )
        ]


class Indicator(TimeStampedUUIDModel):
    """Dynamic indicator definition discovered from templates."""

    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    indicator_type = models.CharField(max_length=50, default="score")
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=5)
    weight = models.DecimalField(max_digits=6, decimal_places=2, default=1)

    class Meta:
        ordering = ["code"]


class AssessmentRecord(TimeStampedUUIDModel):
    """Generic student-period-indicator score storage."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="assessment_records",
    )
    period = models.ForeignKey(
        AssessmentPeriod,
        on_delete=models.PROTECT,
        related_name="records",
    )
    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.PROTECT,
        related_name="records",
    )
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dynamic_assessment_records",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "period", "indicator"],
                name="uq_student_period_indicator_record",
            )
        ]
