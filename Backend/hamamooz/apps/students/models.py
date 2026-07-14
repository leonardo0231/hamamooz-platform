from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel, TimeStampedUUIDModel
from hamamooz.apps.organizations.models import validate_image_size

national_id_validator = RegexValidator(r"^\d{10}$", "کد ملی باید دقیقاً ۱۰ رقم باشد.")


class Student(SoftDeleteModel):
    class Gender(models.TextChoices):
        FEMALE = "female", "دختر"
        MALE = "male", "پسر"

    class Status(models.TextChoices):
        ACTIVE = "active", "فعال"
        GRADUATED = "graduated", "فارغ‌التحصیل"
        TRANSFERRED = "transferred", "انتقالی"
        WITHDRAWN = "withdrawn", "ترک‌تحصیل"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="students"
    )
    national_id = models.CharField(max_length=10, validators=[national_id_validator])
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    photo = models.ImageField(
        upload_to="students/photos/", blank=True, validators=[validate_image_size]
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "national_id"], name="uq_student_org_national_id"
            )
        ]
        indexes = [
            models.Index(fields=["organization", "last_name", "first_name"]),
            models.Index(fields=["organization", "status"]),
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.full_name} - {self.national_id}"


class Guardian(SoftDeleteModel):
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="guardians"
    )
    national_id = models.CharField(
        max_length=10, validators=[national_id_validator], null=True, blank=True
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_primary = models.CharField(max_length=30)
    phone_secondary = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "national_id"],
                condition=models.Q(national_id__isnull=False, is_deleted=False),
                name="uq_guardian_org_national_id",
            )
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.full_name


class StudentGuardian(TimeStampedUUIDModel):
    class Relationship(models.TextChoices):
        FATHER = "father", "پدر"
        MOTHER = "mother", "مادر"
        GUARDIAN = "guardian", "سرپرست"
        OTHER = "other", "سایر"

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="guardian_links")
    guardian = models.ForeignKey(Guardian, on_delete=models.PROTECT, related_name="student_links")
    relationship = models.CharField(max_length=20, choices=Relationship.choices)
    is_primary = models.BooleanField(default=False)
    can_pick_up = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "guardian"], name="uq_student_guardian")
        ]

    def clean(self):
        if (
            self.student_id
            and self.guardian_id
            and self.student.organization_id != self.guardian.organization_id
        ):
            raise ValidationError("دانش‌آموز و ولی باید متعلق به یک مجموعه باشند.")


class Enrollment(SoftDeleteModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "فعال"
        TRANSFERRED = "transferred", "انتقال‌یافته"
        WITHDRAWN = "withdrawn", "ترک‌تحصیل"
        GRADUATED = "graduated", "فارغ‌التحصیل"

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="enrollments")
    school = models.ForeignKey(
        "organizations.School", on_delete=models.PROTECT, related_name="enrollments"
    )
    academic_year = models.ForeignKey(
        "organizations.AcademicYear", on_delete=models.PROTECT, related_name="enrollments"
    )
    grade_level = models.ForeignKey(
        "organizations.GradeLevel", on_delete=models.PROTECT, related_name="enrollments"
    )
    class_section = models.ForeignKey(
        "organizations.ClassSection", on_delete=models.PROTECT, related_name="enrollments"
    )
    student_number = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    enrolled_on = models.DateField()
    left_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-academic_year__starts_on", "class_section", "student__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "academic_year", "school"],
                name="uq_enrollment_student_year_school",
            ),
            models.UniqueConstraint(
                fields=["student", "academic_year"],
                condition=models.Q(status="active", is_deleted=False),
                name="uq_active_enrollment_student_year",
            ),
            models.UniqueConstraint(
                fields=["school", "academic_year", "student_number"],
                condition=models.Q(is_deleted=False),
                name="uq_student_number_school_year",
            ),
        ]
        indexes = [
            models.Index(fields=["school", "academic_year", "class_section", "status"]),
            models.Index(fields=["student", "academic_year", "status"]),
        ]

    def clean(self):
        errors = {}
        if not all(
            [
                self.student_id,
                self.school_id,
                self.academic_year_id,
                self.grade_level_id,
                self.class_section_id,
            ]
        ):
            return
        organization_id = self.school.organization_id
        if self.student.organization_id != organization_id:
            errors["student"] = "دانش‌آموز متعلق به مجموعه این شعبه نیست."
        if self.academic_year.organization_id != organization_id:
            errors["academic_year"] = "سال تحصیلی متعلق به مجموعه این شعبه نیست."
        if self.grade_level.organization_id != organization_id:
            errors["grade_level"] = "پایه متعلق به مجموعه این شعبه نیست."
        if self.class_section.school_id != self.school_id:
            errors["class_section"] = "کلاس متعلق به شعبه انتخاب‌شده نیست."
        elif self.class_section.academic_year_id != self.academic_year_id:
            errors["class_section"] = "کلاس متعلق به سال تحصیلی انتخاب‌شده نیست."
        elif self.class_section.grade_level_id != self.grade_level_id:
            errors["class_section"] = "کلاس متعلق به پایه انتخاب‌شده نیست."
        if self.left_on and self.left_on < self.enrolled_on:
            errors["left_on"] = "تاریخ خروج نمی‌تواند قبل از تاریخ ثبت‌نام باشد."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.student} - {self.academic_year} - {self.class_section}"


class EnrollmentEvent(TimeStampedUUIDModel):
    class EventType(models.TextChoices):
        CLASS_CHANGED = "class_changed", "تغییر کلاس"
        TRANSFER_OUT = "transfer_out", "انتقال خروجی"
        TRANSFER_IN = "transfer_in", "انتقال ورودی"
        STATUS_CHANGED = "status_changed", "تغییر وضعیت"

    enrollment = models.ForeignKey(Enrollment, on_delete=models.PROTECT, related_name="events")
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    from_class_id = models.UUIDField(null=True, blank=True)
    to_class_id = models.UUIDField(null=True, blank=True)
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    reason = models.TextField()
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="enrollment_events",
    )

    class Meta:
        ordering = ["-created_at"]
