from django.conf import settings
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel


class ImportJob(SoftDeleteModel):
    class ImportType(models.TextChoices):
        STUDENTS = "students", "دانش‌آموزان"
        ENROLLMENTS = "enrollments", "ثبت‌نام و کلاس‌بندی"
        SCORES = "scores", "نمرات اولیه"
        MONTHLY_EVALUATIONS = "monthly_evaluations", "ارزیابی جامع ماهانه"
        COMPREHENSIVE_SCHOOL = "comprehensive_school", "فایل جامع مدرسه"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "آپلود شده"
        ANALYZING = "analyzing", "در حال تحلیل"
        PREVIEW_READY = "preview_ready", "پیش‌نمایش آماده"
        CONFIRMED = "confirmed", "تایید شده"
        PROCESSING = "processing", "در حال پردازش"
        COMPLETED = "completed", "تکمیل‌شده"
        FAILED = "failed", "ناموفق"
        CANCELLED = "cancelled", "لغوشده"

    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT, related_name="import_jobs")
    school = models.ForeignKey("organizations.School", on_delete=models.PROTECT, related_name="import_jobs")
    import_type = models.CharField(max_length=30, choices=ImportType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED, db_index=True)
    source_file = models.FileField(upload_to="imports/%Y/%m/")
    checksum = models.CharField(max_length=64, db_index=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="import_jobs")
    total_rows = models.PositiveIntegerField(default=0)
    successful_rows = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    result_summary = models.JSONField(default=dict, blank=True)
    preview_summary = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["school", "import_type", "status"])]

    def __str__(self):
        return f"{self.get_import_type_display()} - {self.school} - {self.status}"
