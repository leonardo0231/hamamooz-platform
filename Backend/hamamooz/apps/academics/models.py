from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel


class Subject(SoftDeleteModel):
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="subjects"
    )
    code = models.SlugField(max_length=30)
    title = models.CharField(max_length=150)
    default_coefficient = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uq_subject_org_code")
        ]

    def __str__(self):
        return self.title


class GradeSubject(SoftDeleteModel):
    grade_level = models.ForeignKey(
        "organizations.GradeLevel", on_delete=models.PROTECT, related_name="grade_subjects"
    )
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="grade_assignments")
    coefficient = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1"))
    pass_mark = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["grade_level", "subject__title"]
        constraints = [
            models.UniqueConstraint(fields=["grade_level", "subject"], name="uq_grade_subject")
        ]

    def clean(self):
        if (
            self.grade_level_id
            and self.subject_id
            and self.grade_level.organization_id != self.subject.organization_id
        ):
            raise ValidationError("درس و پایه باید متعلق به یک مجموعه باشند.")
        if self.coefficient <= 0:
            raise ValidationError({"coefficient": "ضریب درس باید بزرگ‌تر از صفر باشد."})
        if not Decimal("0") <= self.pass_mark <= Decimal("20"):
            raise ValidationError({"pass_mark": "حد قبولی باید بین صفر تا ۲۰ باشد."})

    def __str__(self):
        return f"{self.grade_level} - {self.subject}"


class CourseOffering(SoftDeleteModel):
    class_section = models.ForeignKey(
        "organizations.ClassSection", on_delete=models.PROTECT, related_name="course_offerings"
    )
    grade_subject = models.ForeignKey(
        GradeSubject, on_delete=models.PROTECT, related_name="course_offerings"
    )
    term = models.ForeignKey(
        "organizations.Term", on_delete=models.PROTECT, related_name="course_offerings"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="course_offerings"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["class_section", "grade_subject__subject__title"]
        constraints = [
            models.UniqueConstraint(
                fields=["class_section", "grade_subject", "term"],
                name="uq_course_class_subject_term",
            )
        ]
        indexes = [models.Index(fields=["teacher", "term", "is_active"])]

    def clean(self):
        errors = {}
        if (
            self.class_section_id
            and self.grade_subject_id
            and self.class_section.grade_level_id != self.grade_subject.grade_level_id
        ):
            errors["grade_subject"] = "درس تعریف‌شده متعلق به پایه کلاس نیست."
        if (
            self.class_section_id
            and self.term_id
            and self.class_section.academic_year_id != self.term.academic_year_id
        ):
            errors["term"] = "نوبت متعلق به سال تحصیلی کلاس نیست."
        if errors:
            raise ValidationError(errors)

    @property
    def school_id(self):
        return self.class_section.school_id

    def __str__(self):
        return f"{self.class_section} - {self.grade_subject.subject} - {self.term}"


class AssessmentType(SoftDeleteModel):
    class Category(models.TextChoices):
        CONTINUOUS = "continuous", "مستمر"
        MIDTERM = "midterm", "میان‌ترم"
        FINAL = "final", "پایانی"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="assessment_types"
    )
    code = models.SlugField(max_length=30)
    title = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=Category.choices)
    default_weight = models.DecimalField(max_digits=7, decimal_places=3, default=Decimal("1"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="uq_assessment_type_org_code"
            )
        ]

    def clean(self):
        if self.default_weight <= 0:
            raise ValidationError({"default_weight": "وزن باید بزرگ‌تر از صفر باشد."})

    def __str__(self):
        return self.title


class Assessment(SoftDeleteModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        SUBMITTED = "submitted", "ارسال‌شده برای تأیید"
        REJECTED = "rejected", "ردشده"
        APPROVED = "approved", "تأییدشده"
        LOCKED = "locked", "قفل‌شده"

    course_offering = models.ForeignKey(
        CourseOffering, on_delete=models.PROTECT, related_name="assessments"
    )
    assessment_type = models.ForeignKey(
        AssessmentType, on_delete=models.PROTECT, related_name="assessments"
    )
    title = models.CharField(max_length=150)
    assessment_date = models.DateField()
    max_score = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("20"))
    weight = models.DecimalField(max_digits=7, decimal_places=3, default=Decimal("1"))
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_assessments"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reviewed_assessments",
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    workflow_version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-assessment_date", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["course_offering", "title", "assessment_date"],
                name="uq_assessment_offering_title_date",
            )
        ]
        indexes = [models.Index(fields=["course_offering", "status", "assessment_date"])]

    def clean(self):
        errors = {}
        if self.max_score <= 0:
            errors["max_score"] = "سقف نمره باید بزرگ‌تر از صفر باشد."
        if self.weight <= 0:
            errors["weight"] = "وزن باید بزرگ‌تر از صفر باشد."
        if self.course_offering_id and self.assessment_type_id:
            school_org_id = self.course_offering.class_section.school.organization_id
            if self.assessment_type.organization_id != school_org_id:
                errors["assessment_type"] = "نوع ارزیابی متعلق به مجموعه این درس نیست."
        if errors:
            raise ValidationError(errors)

    @property
    def school_id(self):
        return self.course_offering.class_section.school_id

    def __str__(self):
        return f"{self.course_offering} - {self.title}"


class Score(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        PRESENT = "present", "دارای نمره"
        EXCUSED_ABSENT = "excused_absent", "غیبت موجه"
        UNEXCUSED_ABSENT = "unexcused_absent", "غیبت غیرموجه"
        NOT_ENTERED = "not_entered", "ثبت‌نشده"

    assessment = models.ForeignKey(Assessment, on_delete=models.PROTECT, related_name="scores")
    enrollment = models.ForeignKey(
        "students.Enrollment", on_delete=models.PROTECT, related_name="scores"
    )
    value = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NOT_ENTERED)
    note = models.CharField(max_length=500, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_scores"
    )
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["enrollment__student__last_name", "enrollment__student__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "enrollment"], name="uq_score_assessment_enrollment"
            ),
            models.CheckConstraint(
                condition=models.Q(value__isnull=True) | models.Q(value__gte=0),
                name="score_value_non_negative",
            ),
        ]
        indexes = [models.Index(fields=["assessment", "status"])]

    def clean(self):
        errors = {}
        if self.assessment_id and self.enrollment_id:
            offering = self.assessment.course_offering
            if self.enrollment.class_section_id != offering.class_section_id:
                errors["enrollment"] = "دانش‌آموز عضو کلاس این ارزیابی نیست."
        if self.status == self.Status.PRESENT:
            if self.value is None:
                errors["value"] = "برای وضعیت دارای نمره، مقدار نمره الزامی است."
            elif self.assessment_id and self.value > self.assessment.max_score:
                errors["value"] = f"نمره نباید بیشتر از {self.assessment.max_score} باشد."
        elif self.value is not None:
            errors["value"] = "برای غیبت یا نمره ثبت‌نشده، مقدار باید خالی باشد."
        if errors:
            raise ValidationError(errors)

    @property
    def school_id(self):
        return self.enrollment.school_id


class ScoreRevision(TimeStampedUUIDModel):
    score = models.ForeignKey(Score, on_delete=models.PROTECT, related_name="history")
    old_value = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    new_value = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30)
    old_note = models.CharField(max_length=500, blank=True)
    new_note = models.CharField(max_length=500, blank=True)
    reason = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="score_revisions",
    )
    assessment_status = models.CharField(max_length=20)

    class Meta:
        ordering = ["-created_at"]


class CalculationPolicy(SoftDeleteModel):
    class RoundingMode(models.TextChoices):
        HALF_UP = "half_up", "نیم به بالا"
        HALF_EVEN = "half_even", "نیم به زوج"
        DOWN = "down", "رو به پایین"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="calculation_policies"
    )
    academic_year = models.ForeignKey(
        "organizations.AcademicYear",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="calculation_policies",
    )
    grade_level = models.ForeignKey(
        "organizations.GradeLevel",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="calculation_policies",
    )
    version = models.CharField(max_length=30)
    title = models.CharField(max_length=150)
    overall_pass_mark = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10"))
    decimal_places = models.PositiveSmallIntegerField(default=2)
    rounding_mode = models.CharField(
        max_length=20, choices=RoundingMode.choices, default=RoundingMode.HALF_UP
    )
    unexcused_absence_as_zero = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["organization", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "version"],
                condition=models.Q(
                    academic_year__isnull=True,
                    grade_level__isnull=True,
                    is_deleted=False,
                ),
                name="uq_calc_policy_org_version",
            ),
            models.UniqueConstraint(
                fields=["organization", "academic_year", "version"],
                condition=models.Q(
                    academic_year__isnull=False,
                    grade_level__isnull=True,
                    is_deleted=False,
                ),
                name="uq_calc_policy_year_version",
            ),
            models.UniqueConstraint(
                fields=["organization", "grade_level", "version"],
                condition=models.Q(
                    academic_year__isnull=True,
                    grade_level__isnull=False,
                    is_deleted=False,
                ),
                name="uq_calc_policy_grade_version",
            ),
            models.UniqueConstraint(
                fields=["organization", "academic_year", "grade_level", "version"],
                condition=models.Q(
                    academic_year__isnull=False,
                    grade_level__isnull=False,
                    is_deleted=False,
                ),
                name="uq_calc_policy_full_version",
            ),
        ]

    def clean(self):
        errors = {}
        if self.academic_year_id and self.academic_year.organization_id != self.organization_id:
            errors["academic_year"] = "سال تحصیلی متعلق به مجموعه سیاست نیست."
        if self.grade_level_id and self.grade_level.organization_id != self.organization_id:
            errors["grade_level"] = "پایه متعلق به مجموعه سیاست نیست."
        if self.decimal_places > 4:
            errors["decimal_places"] = "حداکثر چهار رقم اعشار مجاز است."
        if errors:
            raise ValidationError(errors)


class SubjectResult(TimeStampedUUIDModel):
    enrollment = models.ForeignKey(
        "students.Enrollment", on_delete=models.PROTECT, related_name="subject_results"
    )
    course_offering = models.ForeignKey(
        CourseOffering, on_delete=models.PROTECT, related_name="subject_results"
    )
    average = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    passed = models.BooleanField(default=False)
    formula_version = models.CharField(max_length=30)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "course_offering"], name="uq_subject_result_enrollment_course"
            )
        ]


class TermResult(TimeStampedUUIDModel):
    enrollment = models.ForeignKey(
        "students.Enrollment", on_delete=models.PROTECT, related_name="term_results"
    )
    term = models.ForeignKey(
        "organizations.Term", on_delete=models.PROTECT, related_name="student_results"
    )
    average = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    class_rank = models.PositiveIntegerField(null=True, blank=True)
    passed = models.BooleanField(default=False)
    formula_version = models.CharField(max_length=30)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "term"], name="uq_term_result_enrollment_term"
            )
        ]
        indexes = [models.Index(fields=["term", "average"])]
