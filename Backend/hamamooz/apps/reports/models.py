from django.conf import settings
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel


class ReportArchive(SoftDeleteModel):
    class OutputFormat(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "Word"

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
    output_format = models.CharField(
        max_length=10, choices=OutputFormat.choices, default=OutputFormat.PDF
    )
    snapshot = models.JSONField(default=dict, blank=True)
    output_file = models.FileField(upload_to="reports/%Y/%m/", blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="released_reports",
    )
    released_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["school", "academic_year", "report_type", "status"]),
            models.Index(fields=["enrollment", "term"]),
            models.Index(fields=["enrollment", "released_at"]),
        ]

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.created_at:%Y-%m-%d}"


class ReportBatch(TimeStampedUUIDModel):
    """A durable request to generate one immutable report per enrolled student."""
    class Scope(models.TextChoices):
        CLASS = "class", "Class"
        SCHOOL = "school", "School"
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partially completed"
        FAILED = "failed", "Failed"
    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT, related_name="report_batches")
    school = models.ForeignKey("organizations.School", on_delete=models.PROTECT, related_name="report_batches")
    academic_year = models.ForeignKey("organizations.AcademicYear", on_delete=models.PROTECT, related_name="report_batches")
    term = models.ForeignKey("organizations.Term", on_delete=models.PROTECT, related_name="report_batches")
    class_section = models.ForeignKey("organizations.ClassSection", null=True, blank=True, on_delete=models.PROTECT, related_name="report_batches")
    scope = models.CharField(max_length=10, choices=Scope.choices)
    page_size = models.CharField(max_length=20, default="a3_landscape")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_report_batches")
    zip_file = models.FileField(upload_to="reports/batches/%Y/%m/", blank=True)
    total_count = models.PositiveIntegerField(default=0)
    completed_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["school", "academic_year", "term", "status"])]
    @property
    def progress_percent(self):
        return 100 if not self.total_count else int((self.completed_count + self.failed_count) * 100 / self.total_count)


class ReportBatchItem(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
    batch = models.ForeignKey(ReportBatch, on_delete=models.CASCADE, related_name="items")
    enrollment = models.ForeignKey("students.Enrollment", on_delete=models.PROTECT, related_name="report_batch_items")
    report = models.OneToOneField(ReportArchive, null=True, blank=True, on_delete=models.PROTECT, related_name="batch_item")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    error_message = models.TextField(blank=True)
    class Meta:
        ordering = ["enrollment__student__last_name", "enrollment__student__first_name"]
        constraints = [models.UniqueConstraint(fields=["batch", "enrollment"], name="uq_report_batch_enrollment")]


class ReportTemplate(SoftDeleteModel):
    """A safe, allowlisted report layout configuration; never executable Jinja."""

    class OutputFormat(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "Word"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="report_templates"
    )
    school = models.ForeignKey(
        "organizations.School",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="report_templates",
    )
    code = models.SlugField(max_length=60)
    title = models.CharField(max_length=150)
    report_type = models.CharField(max_length=40, choices=ReportArchive.ReportType.choices)
    output_format = models.CharField(
        max_length=10, choices=OutputFormat.choices, default=OutputFormat.PDF
    )
    blocks = models.JSONField(default=list)
    presentation = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["organization", "school", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "school", "code"],
                condition=models.Q(is_deleted=False),
                name="uq_report_template_scope_code",
            )
        ]
        indexes = [models.Index(fields=["organization", "school", "is_active"])]

    def clean(self):
        from django.core.exceptions import ValidationError

        from .services import ALLOWED_REPORT_BLOCKS, ALLOWED_REPORT_PAGE_SIZES

        errors = {}
        if (
            self.school_id
            and self.organization_id
            and self.school.organization_id != self.organization_id
        ):
            errors["school"] = "School must belong to the template organization."
        blocks = self.blocks or []
        invalid = set(blocks) - ALLOWED_REPORT_BLOCKS
        if invalid:
            errors["blocks"] = f"Unsupported report blocks: {', '.join(sorted(invalid))}."
        if len(blocks) != len(set(blocks)):
            errors["blocks"] = "Report blocks must not be repeated."
        if not blocks:
            errors["blocks"] = "At least one allowlisted report block is required."
        if not isinstance(self.presentation, dict):
            errors["presentation"] = "Presentation must be an object."
        elif self.presentation.get("page_size", "a4_portrait") not in ALLOWED_REPORT_PAGE_SIZES:
            errors["presentation"] = "Unsupported report page size."
        if errors:
            raise ValidationError(errors)


class ReportDraft(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RENDERED = "rendered", "Rendered"

    template = models.ForeignKey(ReportTemplate, on_delete=models.PROTECT, related_name="drafts")
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="report_drafts"
    )
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="report_drafts"
    )
    academic_year = models.ForeignKey(
        "organizations.AcademicYear", on_delete=models.PROTECT, related_name="report_drafts"
    )
    term = models.ForeignKey(
        "organizations.Term", on_delete=models.PROTECT, related_name="report_drafts"
    )
    enrollment = models.ForeignKey(
        "students.Enrollment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="report_drafts",
    )
    class_section = models.ForeignKey(
        "organizations.ClassSection",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="report_drafts",
    )
    snapshot = models.JSONField(default=dict)
    content_overrides = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_report_drafts"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reviewed_report_drafts",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True)
    archive = models.OneToOneField(
        ReportArchive,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="source_draft",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(enrollment__isnull=False, class_section__isnull=True)
                    | models.Q(enrollment__isnull=True, class_section__isnull=False)
                ),
                name="ck_report_draft_exactly_one_subject_scope",
            ),
            models.CheckConstraint(
                condition=models.Q(status="approved", reviewed_at__isnull=False)
                | ~models.Q(status="approved"),
                name="ck_report_draft_approval_timestamp",
            ),
        ]
        indexes = [
            models.Index(fields=["school", "status", "-created_at"]),
            models.Index(fields=["enrollment", "term"]),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if (
            self.school_id
            and self.organization_id
            and self.school.organization_id != self.organization_id
        ):
            errors["school"] = "School must belong to the draft organization."
        if (
            self.term_id
            and self.academic_year_id
            and self.term.academic_year_id != self.academic_year_id
        ):
            errors["term"] = "Term must belong to the draft academic year."
        if self.enrollment_id and self.enrollment.school_id != self.school_id:
            errors["enrollment"] = "Enrollment must belong to the draft school."
        if self.class_section_id and self.class_section.school_id != self.school_id:
            errors["class_section"] = "Class must belong to the draft school."
        if self.template_id and self.template.organization_id != self.organization_id:
            errors["template"] = "Template must belong to the draft organization."
        if (
            self.template_id
            and self.template.school_id
            and self.template.school_id != self.school_id
        ):
            errors["template"] = "Template is not available for the draft school."
        if errors:
            raise ValidationError(errors)
