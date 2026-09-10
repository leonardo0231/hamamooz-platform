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
        "organizations.Organization", on_delete=models.PROTECT, related_name="school_import_jobs"
    )
    import_type = models.CharField(max_length=30, choices=ImportType.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADED, db_index=True
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


class DataSourceManifest(SoftDeleteModel):
    """An immutable, auditable inventory entry for a workbook in ``Data/Excel``.

    ``ImportJob`` represents an interactive uploaded file.  This model is deliberately
    separate: a source workbook may be discovered from the repository data directory
    and must be retained, including invalid/incomplete files, before anyone decides
    whether it is suitable for creating official records.
    """

    class Status(models.TextChoices):
        VALID = "valid", "معتبر"
        INCOMPLETE = "incomplete", "ناقص"
        INVALID = "invalid", "نامعتبر"
        CONFLICT = "conflict", "نیازمند تعیین منبع"

    class IngestStatus(models.TextChoices):
        NOT_PROCESSED = "not_processed", "ثبت رسمی نشده"
        COMPLETED = "completed", "ثبت شد"
        PARTIAL = "partial", "ثبت ناقص با حفظ داده خام"
        FAILED = "failed", "خطا در ثبت"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="data_source_manifests"
    )
    school = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="school_data_source_manifests",
    )
    # This is a relative, POSIX path below Data/Excel.  Do not use an absolute
    # filesystem path, so the same manifest remains portable between deployments.
    source_file = models.CharField(max_length=500)
    checksum = models.CharField(max_length=64, db_index=True)
    file_size = models.PositiveBigIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.VALID, db_index=True
    )
    detected_classes = models.JSONField(default=list, blank=True)
    sheet_manifest = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    student_row_count = models.PositiveIntegerField(default=0)
    scanned_at = models.DateTimeField(auto_now=True)
    # The scanner status describes workbook shape.  These fields separately
    # describe the direct, row-wise write into official tables; a partial write
    # is still useful because the raw manifest remains complete and auditable.
    ingest_status = models.CharField(
        max_length=20,
        choices=IngestStatus.choices,
        default=IngestStatus.NOT_PROCESSED,
        db_index=True,
    )
    ingest_summary = models.JSONField(default=dict, blank=True)
    ingested_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["source_file"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "source_file"],
                condition=models.Q(is_deleted=False),
                name="uq_live_data_source_file_school",
            )
        ]
        indexes = [
            models.Index(fields=["school", "status"]),
            models.Index(
                fields=["school", "ingest_status"],
                name="imports_dat_school_ingest_idx",
            ),
            models.Index(fields=["organization", "checksum"]),
        ]

    def __str__(self):
        return f"{self.source_file} ({self.get_status_display()})"


class DataSourceRow(SoftDeleteModel):
    """Raw and normalized evidence for one non-empty worksheet row.

    Raw values are never replaced by normalized values.  Consumers should use the
    normalized projection for calculations and retain ``source_file`` / ``source_row``
    in every derived report for traceability.
    """

    class RowKind(models.TextChoices):
        STUDENT = "student", "دانش‌آموز"
        EVALUATION = "evaluation", "ارزیابی"
        CLASS = "class", "کلاس"
        OTHER = "other", "سایر"

    manifest = models.ForeignKey(DataSourceManifest, on_delete=models.CASCADE, related_name="rows")
    source_file = models.CharField(max_length=500, db_index=True)
    sheet_name = models.CharField(max_length=200)
    source_row = models.PositiveIntegerField()
    row_kind = models.CharField(max_length=20, choices=RowKind.choices, default=RowKind.OTHER)
    raw_values = models.JSONField(default=dict)
    normalized_data = models.JSONField(default=dict)
    # Queryable projections are intentionally duplicated from normalized_data; JSON
    # lookups are not portable across all supported database engines.
    national_id = models.CharField(max_length=20, blank=True, db_index=True)
    class_code = models.CharField(max_length=50, blank=True, db_index=True)
    month_no = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    enrollment = models.ForeignKey(
        "students.Enrollment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="data_source_rows",
    )

    class Meta:
        ordering = ["manifest", "sheet_name", "source_row"]
        constraints = [
            models.UniqueConstraint(
                fields=["manifest", "sheet_name", "source_row"],
                condition=models.Q(is_deleted=False),
                name="uq_live_data_source_sheet_row",
            )
        ]
        indexes = [
            models.Index(fields=["manifest", "national_id"]),
            models.Index(fields=["manifest", "class_code", "month_no"]),
        ]

    def __str__(self):
        return f"{self.source_file}:{self.sheet_name}:{self.source_row}"


class SubjectExamResult(SoftDeleteModel):
    """One raw, queryable row from a standalone subject-exam workbook.

    These rows intentionally do not become ``academics.Score`` records.  The three
    supplied summer workbooks are assessment exports with one row per student and
    subject, and may contain malformed identifiers or score cells.  Keeping the
    source row and its normalized projection here lets an ingestion run retain every
    row without inventing a domain score when normalization or student matching fails.
    """

    class Status(models.TextChoices):
        VALID = "valid", "معتبر"
        INVALID = "invalid", "دارای خطا"
        UNMATCHED = "unmatched", "دانش‌آموز پیدا نشد"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="subject_exam_results",
    )
    school = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="school_subject_exam_results",
    )
    source_manifest = models.ForeignKey(
        DataSourceManifest,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subject_exam_results",
    )
    # Relative POSIX path below the directory passed to the ingestor.
    source_file = models.CharField(max_length=500, db_index=True)
    source_checksum = models.CharField(max_length=64, db_index=True)
    source_sheet = models.CharField(max_length=200)
    source_row = models.PositiveIntegerField()
    exam_period = models.CharField(max_length=30, default="summer", db_index=True)

    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    national_id_raw = models.CharField(max_length=100, blank=True)
    # ``national_id`` is the normalized, queryable projection.  Invalid values stay
    # in ``national_id_raw`` and ``raw_values`` rather than being truncated.
    national_id = models.CharField(max_length=20, blank=True, db_index=True)
    grade_name = models.CharField(max_length=100, blank=True)
    grade_order = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    class_name = models.CharField(max_length=150, blank=True)
    subject_name = models.CharField(max_length=150, blank=True, db_index=True)
    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subject_exam_results",
    )

    question_count = models.PositiveIntegerField(null=True, blank=True)
    correct_count = models.PositiveIntegerField(null=True, blank=True)
    wrong_count = models.PositiveIntegerField(null=True, blank=True)
    blank_count = models.PositiveIntegerField(null=True, blank=True)
    percentage = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    highest_percentage = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    rank = models.PositiveIntegerField(null=True, blank=True)
    t_score = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    overall_rank = models.PositiveIntegerField(null=True, blank=True)
    score = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    final_score = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)

    # ``raw_values`` contains the original cell values (including formulas); the
    # normalized projection may contain cached formula results and parsed values.
    raw_values = models.JSONField(default=dict, blank=True)
    normalized_values = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=list, blank=True)
    error_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.VALID, db_index=True
    )

    class Meta:
        ordering = ["source_file", "source_sheet", "source_row"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "school",
                    "source_file",
                    "source_checksum",
                    "source_sheet",
                    "source_row",
                ],
                condition=models.Q(is_deleted=False),
                name="uq_live_subject_exam_source_row",
            )
        ]
        indexes = [
            models.Index(
                fields=["school", "status", "grade_order"],
                name="imports_subj_school_status_idx",
            ),
            models.Index(
                fields=["school", "national_id", "subject_name"],
                name="imports_subj_student_idx",
            ),
            models.Index(
                fields=["school", "source_file", "source_row"],
                name="imports_subj_school_source_idx",
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if self.organization_id and self.school_id:
            school_organization_id = self.school.organization_id or self.school_id
            if school_organization_id != self.organization_id:
                errors["school"] = "شعبه و مجموعه آزمون باید متعلق به یک مجموعه باشند."
        if (
            self.student_id
            and self.organization_id
            and self.student.organization_id != self.organization_id
        ):
            errors["student"] = "دانش‌آموز متعلق به مجموعه آزمون نیست."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        identity = self.national_id or self.national_id_raw or "بدون شناسه"
        return f"{self.source_file}:{self.source_row} - {identity} - {self.subject_name}"


class ClassSourceSelection(SoftDeleteModel):
    """Explicit human choice of the primary workbook for a class.

    A scanner may discover multiple candidate files.  It must never choose the last
    file encountered; downstream official-report writers must require this record.
    """

    school = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="school_class_source_selections",
    )
    class_code = models.CharField(max_length=50)
    manifest = models.ForeignKey(
        DataSourceManifest,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="selected_for_classes",
    )
    selected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="class_source_selections",
    )
    selection_note = models.TextField(blank=True)

    class Meta:
        ordering = ["class_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "class_code"],
                condition=models.Q(is_deleted=False),
                name="uq_live_class_primary_source",
            )
        ]

    def clean(self):
        if self.manifest_id and self.school_id != self.manifest.school_id:
            from django.core.exceptions import ValidationError

            raise ValidationError({"manifest": "منبع انتخابی باید متعلق به همین مدرسه باشد."})

    def __str__(self):
        return f"{self.school} - {self.class_code}"


class DataSourceConflict(SoftDeleteModel):
    """A non-destructive warning about overlapping files or students."""

    class ConflictType(models.TextChoices):
        DUPLICATE_FILE = "duplicate_file", "فایل تکراری"
        CLASS_OVERLAP = "class_overlap", "کلاس مشترک"
        STUDENT_OVERLAP = "student_overlap", "دانش‌آموز مشترک"

    class Status(models.TextChoices):
        OPEN = "open", "باز"
        RESOLVED = "resolved", "رفع‌شده"

    school = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="school_data_source_conflicts",
    )
    conflict_type = models.CharField(max_length=30, choices=ConflictType.choices, db_index=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    class_code = models.CharField(max_length=50, blank=True, db_index=True)
    national_id = models.CharField(max_length=20, blank=True, db_index=True)
    manifests = models.ManyToManyField(DataSourceManifest, related_name="conflicts", blank=True)
    details = models.JSONField(default=dict, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ["status", "conflict_type", "class_code", "national_id"]
        indexes = [models.Index(fields=["school", "status", "conflict_type"])]

    def __str__(self):
        return f"{self.get_conflict_type_display()} - {self.class_code or self.national_id}"
