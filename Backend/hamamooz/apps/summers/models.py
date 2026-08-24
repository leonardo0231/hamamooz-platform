from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel


TWENTY_POINT_VALIDATORS = [MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("20"))]


class SummerProgram(SoftDeleteModel):
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="summer_programs"
    )
    academic_year = models.ForeignKey(
        "organizations.AcademicYear",
        on_delete=models.PROTECT,
        related_name="summer_programs",
    )
    title = models.CharField(max_length=150)
    pass_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=TWENTY_POINT_VALIDATORS,
    )

    class Meta:
        ordering = ["-academic_year__starts_on", "school", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "academic_year"],
                condition=models.Q(is_deleted=False),
                name="uq_active_summer_program_school_year",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(pass_threshold__isnull=True)
                    | models.Q(pass_threshold__gte=0, pass_threshold__lte=20)
                ),
                name="ck_summer_program_threshold_0_20",
            ),
        ]
        indexes = [
            models.Index(
                fields=["school", "academic_year", "is_deleted"],
                name="summers_sum_school__c0aa1e_idx",
            )
        ]

    def clean(self):
        if (
            self.school_id
            and self.academic_year_id
            and self.school.organization_id != self.academic_year.organization_id
        ):
            raise ValidationError(
                {"academic_year": "سال تحصیلی باید متعلق به مجموعه شعبه برنامه تابستانی باشد."}
            )

    @property
    def organization_id(self):
        return self.school.organization_id if self.school_id else None

    def __str__(self):
        return f"{self.school} - {self.title}"


class SummerProgramRevision(TimeStampedUUIDModel):
    program = models.ForeignKey(
        SummerProgram, on_delete=models.PROTECT, related_name="threshold_revisions"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="summer_program_revisions",
    )
    old_pass_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=TWENTY_POINT_VALIDATORS,
    )
    new_pass_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=TWENTY_POINT_VALIDATORS,
    )
    reason = models.CharField(max_length=500)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(old_pass_threshold__isnull=True)
                    | models.Q(old_pass_threshold__gte=0, old_pass_threshold__lte=20)
                ),
                name="ck_summer_revision_old_threshold_0_20",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(new_pass_threshold__isnull=True)
                    | models.Q(new_pass_threshold__gte=0, new_pass_threshold__lte=20)
                ),
                name="ck_summer_revision_new_threshold_0_20",
            ),
        ]

    @property
    def organization_id(self):
        return self.program.organization_id

    @property
    def school_id(self):
        return self.program.school_id


class SummerCourse(SoftDeleteModel):
    program = models.ForeignKey(
        SummerProgram, on_delete=models.PROTECT, related_name="courses"
    )
    subject = models.ForeignKey(
        "academics.Subject", on_delete=models.PROTECT, related_name="summer_courses"
    )

    class Meta:
        ordering = ["program", "subject__title"]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "subject"],
                condition=models.Q(is_deleted=False),
                name="uq_active_summer_course_program_subject",
            )
        ]
        indexes = [
            models.Index(
                fields=["program", "is_deleted"],
                name="summers_sum_program_53fda3_idx",
            )
        ]

    def clean(self):
        if (
            self.program_id
            and self.subject_id
            and self.program.organization_id != self.subject.organization_id
        ):
            raise ValidationError(
                {"subject": "درس باید متعلق به مجموعه برنامه تابستانی باشد."}
            )

    @property
    def organization_id(self):
        return self.program.organization_id

    @property
    def school_id(self):
        return self.program.school_id

    def __str__(self):
        return f"{self.program} - {self.subject}"


class SummerRegistration(SoftDeleteModel):
    program = models.ForeignKey(
        SummerProgram, on_delete=models.PROTECT, related_name="registrations"
    )
    enrollment = models.ForeignKey(
        "students.Enrollment",
        on_delete=models.PROTECT,
        related_name="summer_registrations",
    )

    class Meta:
        ordering = ["program", "enrollment__student__last_name", "enrollment__student__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "enrollment"],
                condition=models.Q(is_deleted=False),
                name="uq_active_summer_registration_program_enrollment",
            )
        ]
        indexes = [
            models.Index(
                fields=["program", "is_deleted"],
                name="summers_sum_program_c91a73_idx",
            ),
            models.Index(
                fields=["enrollment", "is_deleted"],
                name="summers_sum_enrollm_5bec47_idx",
            ),
        ]

    def clean(self):
        if not self.program_id or not self.enrollment_id:
            return
        errors = {}
        if self.program.school_id != self.enrollment.school_id:
            errors["enrollment"] = "ثبت‌نام تحصیلی باید متعلق به شعبه برنامه تابستانی باشد."
        elif self.program.academic_year_id != self.enrollment.academic_year_id:
            errors["enrollment"] = "ثبت‌نام تحصیلی باید متعلق به سال برنامه تابستانی باشد."
        duplicate_student = SummerRegistration.objects.filter(
            program_id=self.program_id,
            enrollment__student_id=self.enrollment.student_id,
        )
        if self.pk:
            duplicate_student = duplicate_student.exclude(pk=self.pk)
        if duplicate_student.exists():
            errors["enrollment"] = "این دانش‌آموز قبلاً در برنامه تابستانی ثبت‌نام شده است."
        if errors:
            raise ValidationError(errors)

    @property
    def organization_id(self):
        return self.program.organization_id

    @property
    def school_id(self):
        return self.program.school_id

    def __str__(self):
        return f"{self.program} - {self.enrollment.student}"


class SummerCourseRegistration(SoftDeleteModel):
    registration = models.ForeignKey(
        SummerRegistration,
        on_delete=models.PROTECT,
        related_name="course_registrations",
    )
    course = models.ForeignKey(
        SummerCourse, on_delete=models.PROTECT, related_name="registrations"
    )

    class Meta:
        ordering = ["registration", "course__subject__title"]
        constraints = [
            models.UniqueConstraint(
                fields=["registration", "course"],
                condition=models.Q(is_deleted=False),
                name="uq_active_summer_course_registration",
            )
        ]
        indexes = [
            models.Index(
                fields=["registration", "is_deleted"],
                name="summers_sum_registr_9440ef_idx",
            ),
            models.Index(
                fields=["course", "is_deleted"],
                name="summers_sum_course__fb2f5d_idx",
            ),
        ]

    def clean(self):
        if (
            self.registration_id
            and self.course_id
            and self.registration.program_id != self.course.program_id
        ):
            raise ValidationError(
                {"course": "درس انتخابی باید متعلق به برنامه همین ثبت‌نام تابستانی باشد."}
            )

    @property
    def organization_id(self):
        return self.registration.organization_id

    @property
    def school_id(self):
        return self.registration.school_id


class SummerComprehensiveExam(SoftDeleteModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        FINALIZED = "finalized", "نهایی‌شده"

    program = models.ForeignKey(
        SummerProgram, on_delete=models.PROTECT, related_name="exams"
    )
    title = models.CharField(max_length=150)
    exam_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="finalized_summer_exams",
    )

    class Meta:
        ordering = ["-exam_date", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["program"],
                condition=models.Q(is_deleted=False),
                name="uq_active_summer_exam_program",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(status="finalized")
                    | models.Q(finalized_at__isnull=False, finalized_by__isnull=False)
                ),
                name="ck_summer_exam_finalized_evidence",
            ),
        ]
        indexes = [
            models.Index(
                fields=["program", "status", "is_deleted"],
                name="summers_sum_program_6d1055_idx",
            )
        ]

    @property
    def organization_id(self):
        return self.program.organization_id

    def clean(self):
        if self.status == self.Status.FINALIZED and (
            self.finalized_at is None or self.finalized_by_id is None
        ):
            raise ValidationError(
                {
                    "status": (
                        "آزمون جامع نهایی‌شده باید زمان و مسئول نهایی‌سازی معتبر داشته باشد."
                    )
                }
            )

    @property
    def school_id(self):
        return self.program.school_id


class SummerSubjectScore(TimeStampedUUIDModel):
    exam = models.ForeignKey(
        SummerComprehensiveExam, on_delete=models.PROTECT, related_name="subject_scores"
    )
    course_registration = models.ForeignKey(
        SummerCourseRegistration,
        on_delete=models.PROTECT,
        related_name="subject_scores",
    )
    value = models.DecimalField(
        max_digits=4, decimal_places=2, validators=TWENTY_POINT_VALIDATORS
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_summer_scores",
    )

    class Meta:
        ordering = [
            "course_registration__registration__enrollment__student__last_name",
            "course_registration__course__subject__title",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "course_registration"],
                name="uq_summer_score_exam_course_registration",
            ),
            models.CheckConstraint(
                condition=models.Q(value__gte=0, value__lte=20),
                name="ck_summer_subject_score_0_20",
            ),
        ]
        indexes = [
            models.Index(
                fields=["exam", "course_registration"],
                name="summers_sum_exam_id_3a3887_idx",
            )
        ]

    def clean(self):
        if not self.exam_id or not self.course_registration_id:
            return
        registration = self.course_registration.registration
        course = self.course_registration.course
        if registration.program_id != course.program_id:
            raise ValidationError(
                {"course_registration": "ثبت‌نام درس تابستانی دارای برنامه ناسازگار است."}
            )
        if self.exam.program_id != registration.program_id:
            raise ValidationError(
                {"exam": "آزمون و ثبت‌نام درس باید متعلق به یک برنامه تابستانی باشند."}
            )

    @property
    def organization_id(self):
        return self.course_registration.organization_id

    @property
    def school_id(self):
        return self.course_registration.school_id
