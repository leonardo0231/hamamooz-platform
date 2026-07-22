from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel

from .validators import attendance_evidence_upload_to, validate_attendance_evidence


class AttendancePolicy(SoftDeleteModel):
    school = models.ForeignKey(
        "organizations.School",
        on_delete=models.PROTECT,
        related_name="attendance_policies",
    )
    academic_year = models.ForeignKey(
        "organizations.AcademicYear",
        on_delete=models.PROTECT,
        related_name="attendance_policies",
    )
    warning_absence_count = models.PositiveSmallIntegerField(default=3)
    critical_absence_count = models.PositiveSmallIntegerField(default=5)
    warning_absence_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("10.00")
    )
    critical_absence_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("20.00")
    )
    lookback_days = models.PositiveSmallIntegerField(default=30)
    include_excused_absences = models.BooleanField(default=True)
    require_evidence_for_excuse = models.BooleanField(default=False)
    notify_guardians = models.BooleanField(default=True)
    notification_channels = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["school", "-academic_year__starts_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "academic_year"],
                condition=models.Q(is_deleted=False),
                name="uq_attendance_policy_school_year",
            )
        ]

    @property
    def organization_id(self):
        return self.school.organization_id

    def clean(self):
        errors = {}
        if (
            self.school_id
            and self.academic_year_id
            and self.school.organization_id != self.academic_year.organization_id
        ):
            errors["academic_year"] = "سال تحصیلی متعلق به مجموعه این شعبه نیست."
        if self.warning_absence_count < 1:
            errors["warning_absence_count"] = "حد هشدار تعداد غیبت باید حداقل یک باشد."
        if self.lookback_days < 1:
            errors["lookback_days"] = "بازه محاسبه هشدار باید حداقل یک روز باشد."
        if self.warning_absence_count > self.critical_absence_count:
            errors["critical_absence_count"] = "حد بحرانی تعداد غیبت باید از حد هشدار کمتر نباشد."
        if self.warning_absence_percent > self.critical_absence_percent:
            errors["critical_absence_percent"] = "حد بحرانی درصد غیبت باید از حد هشدار کمتر نباشد."
        for field in ["warning_absence_percent", "critical_absence_percent"]:
            value = getattr(self, field)
            if value < 0 or value > 100:
                errors[field] = "درصد باید بین صفر و صد باشد."
        allowed_channels = {"in_app", "email", "sms"}
        invalid_channels = set(self.notification_channels or []) - allowed_channels
        if invalid_channels:
            errors["notification_channels"] = "کانال گزارش به والدین معتبر نیست."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.school} - {self.academic_year}"


class AttendanceSession(SoftDeleteModel):
    class Scope(models.TextChoices):
        DAILY = "daily", "روزانه"
        PERIOD = "period", "زنگ/کلاس"

    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        FINALIZED = "finalized", "نهایی‌شده"
        CANCELLED = "cancelled", "لغوشده"

    school = models.ForeignKey(
        "organizations.School",
        on_delete=models.PROTECT,
        related_name="attendance_sessions",
    )
    academic_year = models.ForeignKey(
        "organizations.AcademicYear",
        on_delete=models.PROTECT,
        related_name="attendance_sessions",
    )
    class_section = models.ForeignKey(
        "organizations.ClassSection",
        on_delete=models.PROTECT,
        related_name="attendance_sessions",
    )
    term = models.ForeignKey(
        "organizations.Term",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="attendance_sessions",
    )
    course_offering = models.ForeignKey(
        "academics.CourseOffering",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="attendance_sessions",
    )
    session_date = models.DateField(db_index=True)
    scope = models.CharField(max_length=20, choices=Scope.choices, db_index=True)
    period_number = models.PositiveSmallIntegerField(null=True, blank=True)
    title = models.CharField(max_length=150, blank=True)
    starts_at = models.TimeField(null=True, blank=True)
    ends_at = models.TimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    taken_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="taken_attendance_sessions",
    )
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="finalized_attendance_sessions",
    )
    finalized_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-session_date", "class_section", "period_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["class_section", "session_date", "scope"],
                condition=models.Q(scope="daily", is_deleted=False),
                name="uq_daily_attendance_class_date",
            ),
            models.UniqueConstraint(
                fields=["class_section", "session_date", "period_number", "scope"],
                condition=models.Q(scope="period", is_deleted=False),
                name="uq_period_attendance_class_date_number",
            ),
        ]
        indexes = [
            models.Index(fields=["school", "academic_year", "session_date", "scope"]),
            models.Index(fields=["class_section", "session_date", "status"]),
        ]

    @property
    def organization_id(self):
        return self.school.organization_id

    def clean(self):
        errors = {}
        if (
            self.school_id
            and self.academic_year_id
            and self.school.organization_id != self.academic_year.organization_id
        ):
            errors["academic_year"] = "سال تحصیلی متعلق به مجموعه این شعبه نیست."
        if self.class_section_id:
            if self.school_id and self.class_section.school_id != self.school_id:
                errors["class_section"] = "کلاس متعلق به شعبه انتخاب‌شده نیست."
            if (
                self.academic_year_id
                and self.class_section.academic_year_id != self.academic_year_id
            ):
                errors["class_section"] = "کلاس متعلق به سال تحصیلی انتخاب‌شده نیست."
        if (
            self.term_id
            and self.academic_year_id
            and self.term.academic_year_id != self.academic_year_id
        ):
            errors["term"] = "نوبت متعلق به سال تحصیلی جلسه نیست."
        if self.academic_year_id and not (
            self.academic_year.starts_on <= self.session_date <= self.academic_year.ends_on
        ):
            errors["session_date"] = "تاریخ جلسه باید داخل بازه سال تحصیلی باشد."
        if self.term_id and not (self.term.starts_on <= self.session_date <= self.term.ends_on):
            errors["session_date"] = "تاریخ جلسه باید داخل بازه نوبت انتخاب‌شده باشد."
        if self.scope == self.Scope.DAILY:
            if self.period_number is not None:
                errors["period_number"] = "برای حضور روزانه شماره زنگ نباید ثبت شود."
            if self.course_offering_id:
                errors["course_offering"] = "برای حضور روزانه درس نباید ثبت شود."
        elif self.scope == self.Scope.PERIOD:
            if not self.period_number:
                errors["period_number"] = "شماره زنگ برای حضور کلاسی الزامی است."
            if not self.course_offering_id:
                errors["course_offering"] = "درس ارائه‌شده برای حضور کلاسی الزامی است."
            elif (
                self.class_section_id
                and self.course_offering.class_section_id != self.class_section_id
            ):
                errors["course_offering"] = "درس ارائه‌شده متعلق به این کلاس نیست."
            elif self.term_id and self.course_offering.term_id != self.term_id:
                errors["course_offering"] = "درس ارائه‌شده متعلق به این نوبت نیست."
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            errors["ends_at"] = "زمان پایان باید بعد از زمان شروع باشد."
        if self.status == self.Status.FINALIZED and not self.finalized_at:
            errors["status"] = "جلسه نهایی‌شده باید زمان نهایی‌سازی داشته باشد."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.class_section} - {self.session_date} - {self.get_scope_display()}"


class AttendanceRecord(SoftDeleteModel):
    class Status(models.TextChoices):
        PRESENT = "present", "حاضر"
        ABSENT_EXCUSED = "absent_excused", "غیبت موجه"
        ABSENT_UNEXCUSED = "absent_unexcused", "غیبت غیرموجه"

    class ExcuseStatus(models.TextChoices):
        NOT_REQUIRED = "not_required", "نیاز ندارد"
        PENDING = "pending", "در انتظار تأیید"
        APPROVED = "approved", "تأییدشده"
        REJECTED = "rejected", "ردشده"

    session = models.ForeignKey(AttendanceSession, on_delete=models.PROTECT, related_name="records")
    enrollment = models.ForeignKey(
        "students.Enrollment",
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.PRESENT, db_index=True
    )
    arrival_time = models.TimeField(null=True, blank=True)
    departure_time = models.TimeField(null=True, blank=True)
    late_minutes = models.PositiveSmallIntegerField(default=0)
    early_leave_minutes = models.PositiveSmallIntegerField(default=0)
    note = models.CharField(max_length=500, blank=True)
    absence_reason = models.TextField(blank=True)
    excuse_status = models.CharField(
        max_length=20,
        choices=ExcuseStatus.choices,
        default=ExcuseStatus.NOT_REQUIRED,
        db_index=True,
    )
    excuse_submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="submitted_attendance_excuses",
    )
    excuse_submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reviewed_attendance_excuses",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = [
            "session",
            "enrollment__student__last_name",
            "enrollment__student__first_name",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "enrollment"],
                condition=models.Q(is_deleted=False),
                name="uq_attendance_record_session_enrollment",
            )
        ]
        indexes = [
            models.Index(fields=["session", "status"]),
            models.Index(fields=["enrollment", "status"]),
            models.Index(fields=["excuse_status", "updated_at"]),
        ]

    @property
    def school_id(self):
        return self.session.school_id

    @property
    def organization_id(self):
        return self.session.school.organization_id

    @property
    def student_id(self):
        return self.enrollment.student_id

    @property
    def is_late(self):
        return self.late_minutes > 0

    @property
    def left_early(self):
        return self.early_leave_minutes > 0

    def clean(self):
        errors = {}
        if self.session_id and self.enrollment_id:
            if self.enrollment.school_id != self.session.school_id:
                errors["enrollment"] = "ثبت‌نام متعلق به شعبه جلسه حضور و غیاب نیست."
            elif self.enrollment.academic_year_id != self.session.academic_year_id:
                errors["enrollment"] = "ثبت‌نام متعلق به سال تحصیلی جلسه نیست."
            elif self.enrollment.class_section_id != self.session.class_section_id:
                errors["enrollment"] = "دانش‌آموز عضو کلاس این جلسه نیست."
        is_absent = self.status in {
            self.Status.ABSENT_EXCUSED,
            self.Status.ABSENT_UNEXCUSED,
        }
        if is_absent:
            if (
                self.arrival_time
                or self.departure_time
                or self.late_minutes
                or self.early_leave_minutes
            ):
                errors["status"] = "برای دانش‌آموز غایب، تأخیر یا خروج زودهنگام ثبت نمی‌شود."
        else:
            if self.excuse_status != self.ExcuseStatus.NOT_REQUIRED:
                errors["excuse_status"] = "برای دانش‌آموز حاضر وضعیت توجیه غیبت معتبر نیست."
            if self.absence_reason:
                errors["absence_reason"] = "برای دانش‌آموز حاضر دلیل غیبت ثبت نمی‌شود."
        if (
            self.status == self.Status.ABSENT_EXCUSED
            and self.excuse_status != self.ExcuseStatus.APPROVED
        ):
            errors["excuse_status"] = "غیبت موجه فقط پس از تأیید مسئول قابل ثبت است."
        if self.excuse_status == self.ExcuseStatus.APPROVED:
            if self.status != self.Status.ABSENT_EXCUSED:
                errors["status"] = "غیبت تأییدشده باید موجه باشد."
            if not self.reviewed_by_id or not self.reviewed_at:
                errors["reviewed_by"] = "تأیید غیبت باید همراه با مسئول و زمان بررسی باشد."
        if (
            self.excuse_status in {self.ExcuseStatus.PENDING, self.ExcuseStatus.REJECTED}
            and self.status != self.Status.ABSENT_UNEXCUSED
        ):
            errors["status"] = "تا پیش از تأیید، غیبت غیرموجه محسوب می‌شود."
        if self.excuse_status == self.ExcuseStatus.PENDING and (
            not self.absence_reason or not self.excuse_submitted_at
        ):
            errors["absence_reason"] = "برای درخواست توجیه، دلیل غیبت الزامی است."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.enrollment.student} - {self.session} - {self.get_status_display()}"


class AbsenceEvidence(SoftDeleteModel):
    attendance_record = models.ForeignKey(
        AttendanceRecord, on_delete=models.PROTECT, related_name="evidence_files"
    )
    file = models.FileField(
        upload_to=attendance_evidence_upload_to,
        validators=[validate_attendance_evidence],
        max_length=500,
    )
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveIntegerField()
    description = models.CharField(max_length=300, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_absence_evidence",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["attendance_record", "created_at"])]

    @property
    def school_id(self):
        return self.attendance_record.school_id

    @property
    def organization_id(self):
        return self.attendance_record.organization_id

    def clean(self):
        if (
            self.attendance_record_id
            and self.attendance_record.status == AttendanceRecord.Status.PRESENT
        ):
            raise ValidationError("برای وضعیت حاضر نمی‌توان مدرک غیبت بارگذاری کرد.")


class AttendanceRecordRevision(TimeStampedUUIDModel):
    attendance_record = models.ForeignKey(
        AttendanceRecord, on_delete=models.PROTECT, related_name="history"
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="attendance_revisions",
    )
    reason = models.TextField()
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]


class AttendanceAlert(SoftDeleteModel):
    class Scope(models.TextChoices):
        DAILY = AttendanceSession.Scope.DAILY, "روزانه"
        PERIOD = AttendanceSession.Scope.PERIOD, "زنگ/کلاس"

    class Severity(models.TextChoices):
        WARNING = "warning", "هشدار"
        CRITICAL = "critical", "بحرانی"

    class Status(models.TextChoices):
        OPEN = "open", "باز"
        ACKNOWLEDGED = "acknowledged", "مشاهده‌شده"
        RESOLVED = "resolved", "رفع‌شده"

    policy = models.ForeignKey(AttendancePolicy, on_delete=models.PROTECT, related_name="alerts")
    school = models.ForeignKey(
        "organizations.School",
        on_delete=models.PROTECT,
        related_name="attendance_alerts",
    )
    academic_year = models.ForeignKey(
        "organizations.AcademicYear",
        on_delete=models.PROTECT,
        related_name="attendance_alerts",
    )
    enrollment = models.ForeignKey(
        "students.Enrollment",
        on_delete=models.PROTECT,
        related_name="attendance_alerts",
    )
    scope = models.CharField(max_length=20, choices=Scope.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices, db_index=True)
    period_start = models.DateField()
    period_end = models.DateField()
    absence_count = models.PositiveIntegerField()
    total_sessions = models.PositiveIntegerField()
    absence_percent = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="acknowledged_attendance_alerts",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="resolved_attendance_alerts",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["policy", "enrollment", "scope", "severity"],
                condition=models.Q(status__in=["open", "acknowledged"], is_deleted=False),
                name="uq_active_attendance_alert",
            )
        ]
        indexes = [
            models.Index(fields=["school", "academic_year", "status", "severity"]),
            models.Index(fields=["enrollment", "scope", "status"]),
        ]

    @property
    def organization_id(self):
        return self.school.organization_id

    @property
    def student_id(self):
        return self.enrollment.student_id

    def clean(self):
        errors = {}
        if self.enrollment_id:
            if self.enrollment.school_id != self.school_id:
                errors["enrollment"] = "ثبت‌نام متعلق به شعبه هشدار نیست."
            if self.enrollment.academic_year_id != self.academic_year_id:
                errors["enrollment"] = "ثبت‌نام متعلق به سال تحصیلی هشدار نیست."
        if self.period_start > self.period_end:
            errors["period_end"] = "پایان بازه هشدار باید بعد از شروع آن باشد."
        if self.total_sessions and self.absence_count > self.total_sessions:
            errors["absence_count"] = "تعداد غیبت نمی‌تواند از کل جلسات بیشتر باشد."
        if errors:
            raise ValidationError(errors)


class ParentNotification(TimeStampedUUIDModel):
    class Kind(models.TextChoices):
        ABSENCE = "absence", "گزارش غیبت"
        SUMMARY = "summary", "گزارش دوره‌ای"
        ALERT = "alert", "هشدار غیبت بیش از حد"

    class Channel(models.TextChoices):
        IN_APP = "in_app", "داخل سامانه"
        EMAIL = "email", "ایمیل"
        SMS = "sms", "پیامک"

    class Status(models.TextChoices):
        QUEUED = "queued", "در صف"
        SENT = "sent", "ارسال‌شده"
        FAILED = "failed", "ناموفق"
        SKIPPED = "skipped", "ردشده"

    school = models.ForeignKey(
        "organizations.School",
        on_delete=models.PROTECT,
        related_name="parent_notifications",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="attendance_notifications",
    )
    enrollment = models.ForeignKey(
        "students.Enrollment",
        on_delete=models.PROTECT,
        related_name="parent_notifications",
    )
    guardian = models.ForeignKey(
        "students.Guardian",
        on_delete=models.PROTECT,
        related_name="attendance_notifications",
    )
    attendance_record = models.ForeignKey(
        AttendanceRecord,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="parent_notifications",
    )
    alert = models.ForeignKey(
        AttendanceAlert,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="parent_notifications",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    channel = models.CharField(max_length=20, choices=Channel.choices, db_index=True)
    recipient = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    dedupe_key = models.CharField(max_length=160, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_parent_notifications",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["school", "status", "created_at"]),
            models.Index(fields=["guardian", "created_at"]),
            models.Index(fields=["channel", "status"]),
        ]

    @property
    def organization_id(self):
        return self.school.organization_id

    def clean(self):
        errors = {}
        if self.enrollment_id:
            if self.enrollment.school_id != self.school_id:
                errors["enrollment"] = "ثبت‌نام متعلق به شعبه اعلان نیست."
            if self.enrollment.student_id != self.student_id:
                errors["student"] = "دانش‌آموز با ثبت‌نام اعلان سازگار نیست."
        if self.attendance_record_id and self.attendance_record.enrollment_id != self.enrollment_id:
            errors["attendance_record"] = "رکورد حضور و غیاب با ثبت‌نام اعلان سازگار نیست."
        if self.alert_id and self.alert.enrollment_id != self.enrollment_id:
            errors["alert"] = "هشدار حضور و غیاب با ثبت‌نام اعلان سازگار نیست."
        if errors:
            raise ValidationError(errors)

    def mark_sent(self):
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.last_error = ""
        self.save(update_fields=["status", "sent_at", "last_error", "updated_at"])
