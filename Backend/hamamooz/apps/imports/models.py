from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel


class ImportJob(SoftDeleteModel):
    class SourceKind(models.TextChoices):
        UPLOAD = "upload", "آپلود کاربر"
        DATA_PATH = "data_path", "مسیر Data مخزن"

    class ImportType(models.TextChoices):
        STUDENTS = "students", "دانش‌آموزان"
        ENROLLMENTS = "enrollments", "ثبت‌نام و کلاس‌بندی"
        SCORES = "scores", "نمرات اولیه"
        MONTHLY_EVALUATIONS = "monthly_evaluations", "ارزیابی جامع ماهانه"
        COMPREHENSIVE_SCHOOL = "comprehensive_school", "فایل جامع مدرسه"

    class Status(models.TextChoices):
        # Legacy workbook workers use an explicit queue state.  Keep it as a
        # compatibility choice while newly uploaded jobs still start at
        # ``uploaded`` and pass through preview/confirmation.
        QUEUED = "queued", "در صف"
        UPLOADED = "uploaded", "آپلود شده"
        ANALYZING = "analyzing", "در حال تحلیل"
        PREVIEW_READY = "preview_ready", "پیش‌نمایش آماده"
        CONFIRMED = "confirmed", "تایید شده"
        PROCESSING = "processing", "در حال پردازش"
        COMPLETED = "completed", "تکمیل‌شده"
        FAILED = "failed", "ناموفق"
        CANCELLED = "cancelled", "لغوشده"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="import_jobs"
    )
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="import_jobs"
    )
    import_type = models.CharField(max_length=30, choices=ImportType.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADED, db_index=True
    )
    source_file = models.FileField(upload_to="imports/%Y/%m/")
    source_kind = models.CharField(
        max_length=20, choices=SourceKind.choices, default=SourceKind.UPLOAD, db_index=True
    )
    data_path_import = models.ForeignKey(
        "imports.DataPathImport",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="file_jobs",
    )
    checksum = models.CharField(max_length=64, db_index=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="import_jobs"
    )
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
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "school", "import_type", "checksum"],
                condition=models.Q(
                    is_deleted=False,
                    status__in=[
                        "uploaded",
                        "analyzing",
                        "preview_ready",
                        "confirmed",
                        "processing",
                        "completed",
                    ],
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


class DataPathImport(TimeStampedUUIDModel):
    """A durable import request for the repository's mounted ``Data`` folder.

    This is deliberately separate from an uploaded-file ImportJob.  The Data
    folder is a source bundle containing many workbooks and a photo tree, so
    it needs one parent record for discovery, reconciliation, and completion
    status while retaining one child ImportJob per workbook for provenance.
    """

    class Status(models.TextChoices):
        QUEUED = "queued", "در صف"
        SCANNING = "scanning", "در حال اسکن مسیر Data"
        PROCESSING = "processing", "در حال ثبت اطلاعات"
        COMPLETED = "completed", "تکمیل‌شده"
        PARTIAL = "partial", "تکمیل با هشدار"
        FAILED = "failed", "ناموفق"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="data_path_imports"
    )
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="data_path_imports"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="data_path_imports",
    )
    source_root = models.CharField(max_length=1000)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True
    )
    overwrite_photos = models.BooleanField(default=False)
    generate_reports = models.BooleanField(default=True)
    report_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    manifest = models.JSONField(default=dict, blank=True)
    result_summary = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["school", "status"],
                name="imp_dp_school_status_idx",
            ),
            models.Index(
                fields=["organization", "created_at"],
                name="imp_dp_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Data import - {self.school} - {self.status}"
