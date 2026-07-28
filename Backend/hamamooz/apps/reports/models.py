from django.conf import settings
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel


class ReportArchive(SoftDeleteModel):
    class ReportType(models.TextChoices):
        STUDENT_REPORT_CARD = "student_report_card", "کارنامه دانش‌آموز"
        CLASS_REPORT_CARDS = "class_report_cards", "کارنامه گروهی کلاس"

    class Status(models.TextChoices):
        QUEUED = "queued", "در صف"
        PROCESSING = "processing", "در حال تولید"
        COMPLETED = "completed", "آماده"
        FAILED = "failed", "ناموفق"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="reports"
    )
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="reports"
    )
    academic_year = models.ForeignKey(
        "organizations.AcademicYear", on_delete=models.PROTECT, related_name="reports"
    )
    term = models.ForeignKey("organizations.Term", on_delete=models.PROTECT, related_name="reports")
    report_type = models.CharField(max_length=40, choices=ReportType.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True
    )
    enrollment = models.ForeignKey(
        "students.Enrollment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reports",
    )
    class_section = models.ForeignKey(
        "organizations.ClassSection",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reports",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_reports"
    )
    formula_version = models.CharField(max_length=30, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)
    output_file = models.FileField(upload_to="reports/%Y/%m/", blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["school", "academic_year", "report_type", "status"]),
            models.Index(fields=["enrollment", "term"]),
        ]

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.created_at:%Y-%m-%d}"
