from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel


class ReportLayoutKey(models.TextChoices):
    ANALYTICAL_TERM_1 = "analytical_term_1", "کارنامه تحلیلی نوبت اول"
    ANALYTICAL_TERM_2 = "analytical_term_2", "کارنامه تحلیلی نوبت دوم"
    ANALYTICAL_ANNUAL = "analytical_annual", "کارنامه تحلیلی سالانه"
    FINAL_TERM_1 = "final_term_1", "کارنامه نهایی نوبت اول"
    FINAL_TERM_2 = "final_term_2", "کارنامه نهایی نوبت دوم"
    FINAL_ANNUAL = "final_annual", "کارنامه نهایی سالانه"
    SUMMER_REPORT = "summer_report", "کارنامه تابستان"


class ReportPeriodType(models.TextChoices):
    TERM = "term", "نوبت"
    ANNUAL = "annual", "سالانه"
    SUMMER = "summer", "تابستان"


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
    term = models.ForeignKey(
        "organizations.Term",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reports",
    )
    summer_program = models.ForeignKey(
        "summers.SummerProgram",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="report_archives",
    )
    summer_registration = models.ForeignKey(
        "summers.SummerRegistration",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="report_archives",
    )
    summer_exam = models.ForeignKey(
        "summers.SummerComprehensiveExam",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="report_archives",
    )
    report_type = models.CharField(max_length=40, choices=ReportType.choices)
    layout_key = models.CharField(max_length=40, choices=ReportLayoutKey.choices, blank=True)
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
    source_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    tracking_code = models.CharField(max_length=40, null=True, blank=True, unique=True)
    report_version = models.PositiveIntegerField(null=True, blank=True)
    output_file = models.FileField(upload_to="reports/%Y/%m/", blank=True)
    editable_output_file = models.FileField(upload_to="reports/%Y/%m/", blank=True)
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
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approved_report_archives",
    )
    approved_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["school", "academic_year", "report_type", "status"]),
            models.Index(fields=["enrollment", "term"]),
            models.Index(fields=["enrollment", "released_at"]),
            models.Index(
                fields=["school", "academic_year", "layout_key", "report_version"],
                name="reports_card_scope_version_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.created_at:%Y-%m-%d}"

    @property
    def period_type(self):
        if self.layout_key == ReportLayoutKey.SUMMER_REPORT or self.summer_program_id:
            return ReportPeriodType.SUMMER
        if self.layout_key in {
            ReportLayoutKey.ANALYTICAL_ANNUAL,
            ReportLayoutKey.FINAL_ANNUAL,
        }:
            return ReportPeriodType.ANNUAL
        return ReportPeriodType.TERM if self.term_id else ReportPeriodType.ANNUAL

    @property
    def period_label(self):
        if self.period_type == ReportPeriodType.SUMMER:
            return self.summer_program.title if self.summer_program_id else "تابستان"
        if self.period_type == ReportPeriodType.ANNUAL:
            return self.academic_year.title
        return self.term.title if self.term_id else ""

    def clean(self):
        errors = {}
        if self.layout_key:
            if self.period_type == ReportPeriodType.TERM and not self.term_id:
                errors["term"] = "A term report requires a term."
            if self.period_type != ReportPeriodType.TERM and self.term_id:
                errors["term"] = "Annual and summer reports must not reference an ordinary term."
            if self.period_type == ReportPeriodType.SUMMER:
                if not self.summer_registration_id or not self.summer_program_id:
                    errors["summer_registration"] = (
                        "A summer report requires a program registration."
                    )
                elif self.summer_registration.program_id != self.summer_program_id:
                    errors["summer_registration"] = (
                        "Summer registration must belong to the report program."
                    )
                elif (
                    self.summer_program.school_id != self.school_id
                    or self.summer_program.academic_year_id != self.academic_year_id
                ):
                    errors["summer_program"] = "Summer program must match report school and year."
                if self.summer_exam_id and self.summer_exam.program_id != self.summer_program_id:
                    errors["summer_exam"] = "Summer exam must belong to the report program."
            elif self.summer_program_id or self.summer_registration_id or self.summer_exam_id:
                errors["summer_program"] = "Only a summer report may reference summer records."
        if self.term_id and self.term.academic_year_id != self.academic_year_id:
            errors["term"] = "Term must belong to the report academic year."
        if self.enrollment_id and self.enrollment.school_id != self.school_id:
            errors["enrollment"] = "Enrollment must belong to the report school."
        if self.class_section_id and self.class_section.school_id != self.school_id:
            errors["class_section"] = "Class must belong to the report school."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk:
            previous = ReportArchive.all_objects.filter(pk=self.pk).values(
                "status",
                "organization_id",
                "school_id",
                "academic_year_id",
                "report_type",
                "snapshot",
                "source_fingerprint",
                "tracking_code",
                "report_version",
                "layout_key",
                "term_id",
                "enrollment_id",
                "class_section_id",
                "summer_program_id",
                "summer_registration_id",
                "summer_exam_id",
                "requested_by_id",
                "formula_version",
                "output_format",
                "output_file",
                "editable_output_file",
                "approved_by_id",
                "approved_at",
            ).first()
            immutable_fields = (
                "organization_id",
                "school_id",
                "academic_year_id",
                "report_type",
                "snapshot",
                "source_fingerprint",
                "tracking_code",
                "report_version",
                "layout_key",
                "term_id",
                "enrollment_id",
                "class_section_id",
                "summer_program_id",
                "summer_registration_id",
                "summer_exam_id",
                "requested_by_id",
                "formula_version",
                "output_format",
                "output_file",
                "editable_output_file",
                "approved_by_id",
                "approved_at",
            )
            if previous and previous["status"] == self.Status.COMPLETED:
                if self.status != self.Status.COMPLETED:
                    raise ValidationError(
                        {"status": "A completed report archive cannot leave its terminal state."}
                    )
                changed = []
                for field in immutable_fields:
                    current = getattr(self, field)
                    if field in {"output_file", "editable_output_file"}:
                        current = current.name
                    if previous[field] != current:
                        changed.append(field)
                if changed:
                    raise ValidationError(
                        {"snapshot": "A completed official report archive is immutable."}
                    )
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if self.status == self.Status.COMPLETED:
            raise ValidationError("A completed official report archive cannot be deleted.")
        return super().delete(using=using, keep_parents=keep_parents)


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
    layout_key = models.CharField(max_length=40, choices=ReportLayoutKey.choices, blank=True)
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
        "organizations.Term",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="report_drafts",
    )
    summer_program = models.ForeignKey(
        "summers.SummerProgram",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="report_drafts",
    )
    summer_registration = models.ForeignKey(
        "summers.SummerRegistration",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="report_drafts",
    )
    summer_exam = models.ForeignKey(
        "summers.SummerComprehensiveExam",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="report_drafts",
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
    source_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    tracking_code = models.CharField(max_length=40, null=True, blank=True, unique=True)
    report_version = models.PositiveIntegerField(null=True, blank=True)
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
                    models.Q(
                        enrollment__isnull=False,
                        class_section__isnull=True,
                        summer_registration__isnull=True,
                    )
                    | models.Q(
                        enrollment__isnull=True,
                        class_section__isnull=False,
                        summer_registration__isnull=True,
                    )
                    | models.Q(
                        enrollment__isnull=True,
                        class_section__isnull=True,
                        summer_registration__isnull=False,
                    )
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
        if self.template_id and self.layout_key and self.template.layout_key != self.layout_key:
            errors["layout_key"] = "Draft layout must match its template."
        if self.layout_key == ReportLayoutKey.SUMMER_REPORT:
            if self.term_id or self.enrollment_id or self.class_section_id:
                errors["term"] = "Summer reports use only a summer registration."
            if not self.summer_registration_id or not self.summer_program_id:
                errors["summer_registration"] = "Summer registration is required."
            elif self.summer_registration.program_id != self.summer_program_id:
                errors["summer_registration"] = "Registration does not belong to the program."
            elif (
                self.summer_program.school_id != self.school_id
                or self.summer_program.academic_year_id != self.academic_year_id
            ):
                errors["summer_program"] = "Summer program must match draft school and year."
            if self.summer_exam_id and self.summer_exam.program_id != self.summer_program_id:
                errors["summer_exam"] = "Summer exam must belong to the draft program."
        elif self.layout_key in {
            ReportLayoutKey.ANALYTICAL_ANNUAL,
            ReportLayoutKey.FINAL_ANNUAL,
        }:
            if self.term_id:
                errors["term"] = "Annual reports must not reference a term."
        elif self.layout_key and not self.term_id:
            errors["term"] = "Term report layouts require a term."
        if errors:
            raise ValidationError(errors)

    @property
    def period_type(self):
        if self.layout_key == ReportLayoutKey.SUMMER_REPORT:
            return ReportPeriodType.SUMMER
        if self.layout_key in {
            ReportLayoutKey.ANALYTICAL_ANNUAL,
            ReportLayoutKey.FINAL_ANNUAL,
        }:
            return ReportPeriodType.ANNUAL
        return ReportPeriodType.TERM

    @property
    def period_label(self):
        if self.period_type == ReportPeriodType.SUMMER:
            return self.summer_program.title if self.summer_program_id else "تابستان"
        if self.period_type == ReportPeriodType.ANNUAL:
            return self.academic_year.title
        return self.term.title if self.term_id else ""

    def save(self, *args, **kwargs):
        if self.pk:
            previous = ReportDraft.objects.filter(pk=self.pk).values(
                "status",
                "template_id",
                "organization_id",
                "school_id",
                "academic_year_id",
                "layout_key",
                "term_id",
                "enrollment_id",
                "class_section_id",
                "summer_program_id",
                "summer_registration_id",
                "summer_exam_id",
                "snapshot",
                "source_fingerprint",
                "content_overrides",
                "tracking_code",
                "report_version",
                "reviewed_by_id",
                "reviewed_at",
                "archive_id",
            ).first()
            immutable_fields = (
                tuple(field for field in previous if field not in {"status", "archive_id"})
                if previous
                else ()
            )
            if previous and previous["status"] in {self.Status.APPROVED, self.Status.RENDERED}:
                allowed_statuses = (
                    {self.Status.APPROVED, self.Status.RENDERED}
                    if previous["status"] == self.Status.APPROVED
                    else {self.Status.RENDERED}
                )
                if self.status not in allowed_statuses:
                    raise ValidationError(
                        {"status": "An approved report may only advance to rendered."}
                    )
                changed = [
                    field for field in immutable_fields if previous[field] != getattr(self, field)
                ]
                if (
                    previous["status"] == self.Status.RENDERED
                    and previous["archive_id"] != self.archive_id
                ):
                    changed.append("archive_id")
                if changed:
                    raise ValidationError({"snapshot": "An approved report snapshot is immutable."})
        return super().save(*args, **kwargs)
