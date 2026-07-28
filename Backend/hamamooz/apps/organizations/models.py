from django.core.exceptions import ValidationError
from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel


def validate_image_size(value):
    if value and value.size > 2 * 1024 * 1024:
        raise ValidationError("حجم تصویر نباید بیشتر از ۲ مگابایت باشد.")


class Organization(SoftDeleteModel):
    name = models.CharField(max_length=200)
    code = models.SlugField(max_length=50, unique=True)
    logo = models.ImageField(
        upload_to="organizations/logos/", blank=True, validators=[validate_image_size]
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class School(SoftDeleteModel):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="schools")
    code = models.SlugField(max_length=50)
    name = models.CharField(max_length=200)
    official_name = models.CharField(max_length=250, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    manager_name = models.CharField(max_length=150, blank=True)
    logo = models.ImageField(
        upload_to="schools/logos/", blank=True, validators=[validate_image_size]
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["organization", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uq_school_org_code")
        ]

    def __str__(self):
        return f"{self.organization} - {self.name}"


class AcademicYear(SoftDeleteModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="academic_years"
    )
    code = models.SlugField(max_length=20)
    title = models.CharField(max_length=50)
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_current = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-starts_on"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uq_year_org_code"),
            models.UniqueConstraint(
                fields=["organization"],
                condition=models.Q(is_current=True, is_deleted=False),
                name="uq_current_year_per_org",
            ),
        ]

    def clean(self):
        if self.starts_on >= self.ends_on:
            raise ValidationError({"ends_on": "تاریخ پایان باید بعد از تاریخ شروع باشد."})

    def __str__(self):
        return self.title


class Term(SoftDeleteModel):
    class Code(models.TextChoices):
        FIRST = "first", "نوبت اول"
        SECOND = "second", "نوبت دوم"

    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="terms")
    code = models.CharField(max_length=20, choices=Code.choices)
    title = models.CharField(max_length=50)
    starts_on = models.DateField()
    ends_on = models.DateField()
    order = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["academic_year", "order"]
        constraints = [
            models.UniqueConstraint(fields=["academic_year", "code"], name="uq_term_year_code")
        ]

    def clean(self):
        errors = {}
        if self.starts_on >= self.ends_on:
            errors["ends_on"] = "تاریخ پایان باید بعد از تاریخ شروع باشد."
        if self.academic_year_id and (
            self.starts_on < self.academic_year.starts_on
            or self.ends_on > self.academic_year.ends_on
        ):
            errors["starts_on"] = "بازه نوبت باید داخل سال تحصیلی باشد."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.academic_year} - {self.title}"


class GradeLevel(SoftDeleteModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="grade_levels"
    )
    code = models.SlugField(max_length=30)
    title = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uq_grade_org_code"),
            models.UniqueConstraint(fields=["organization", "order"], name="uq_grade_org_order"),
        ]

    def __str__(self):
        return self.title


class ClassSection(SoftDeleteModel):
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name="classes")
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.PROTECT, related_name="classes"
    )
    grade_level = models.ForeignKey(GradeLevel, on_delete=models.PROTECT, related_name="classes")
    code = models.SlugField(max_length=30)
    title = models.CharField(max_length=100)
    capacity = models.PositiveSmallIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["school", "grade_level__order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "academic_year", "code"], name="uq_class_school_year_code"
            )
        ]
        indexes = [models.Index(fields=["school", "academic_year", "grade_level"])]

    def clean(self):
        if (
            self.school_id
            and self.academic_year_id
            and self.school.organization_id != self.academic_year.organization_id
        ):
            raise ValidationError("سال تحصیلی با مجموعه شعبه یکسان نیست.")
        if (
            self.school_id
            and self.grade_level_id
            and self.school.organization_id != self.grade_level.organization_id
        ):
            raise ValidationError("پایه با مجموعه شعبه یکسان نیست.")

    def __str__(self):
        return f"{self.school.name} - {self.title}"
