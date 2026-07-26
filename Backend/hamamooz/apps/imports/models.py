from django.conf import settings
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel


class ImportJob(SoftDeleteModel):
    class ImportType(models.TextChoices):
        STUDENTS = "students", "دانش‌آموزان"
        ENROLLMENTS = "enrollments", "ثبت‌نام و کلاس‌بندی"
        SCORES = "scores", "نمرات اولیه"
        MONTHLY_EVALUATIONS = "monthly_evaluations", "ارزیابی جامع ماهانه"

    class Status(models.TextChoices):
        QUEUED = "queued", "در صف"
        PROCESSING = "processing", "در حال پردازش"
        COMPLETED = "completed", "تکمیل‌شده"
        FAILED = "failed", "ناموفق"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="import_jobs"
    )
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="import_jobs"
    )
    import_type = models.CharField(max_length=30, choices=ImportType.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True
    )
    source_file = models.FileField(upload_to="imports/%Y/%m/")
    checksum = models.CharField(max_length=64, db_index=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="import_jobs"
    )
    total_rows = models.PositiveIntegerField(default=0)
    successful_rows = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "school", "import_type", "checksum"],
                condition=models.Q(
                    is_deleted=False,
                    status__in=["queued", "processing", "completed"],
                ),
                name="uq_active_import_file_scope",
            )
        ]
        indexes = [
            models.Index(fields=["school", "import_type", "status"]),
            models.Index(fields=["organization", "checksum", "import_type"]),
        ]

    def __str__(self):
        return f"{self.get_import_type_display()} - {self.school} - {self.status}"
