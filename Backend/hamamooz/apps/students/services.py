from django.db import transaction
from rest_framework.exceptions import ValidationError

from hamamooz.apps.organizations.models import ClassSection

from .models import Enrollment, EnrollmentEvent


def _locked_enrollment(enrollment):
    return (
        Enrollment.objects.select_for_update()
        .select_related("student", "school", "academic_year", "grade_level", "class_section")
        .get(pk=enrollment.pk)
    )


def _locked_class(class_section):
    return (
        ClassSection.objects.select_for_update()
        .select_related("school", "academic_year", "grade_level")
        .get(pk=class_section.pk)
    )


def _ensure_capacity(class_section):
    active_count = Enrollment.objects.filter(
        class_section=class_section, status=Enrollment.Status.ACTIVE
    ).count()
    if active_count >= class_section.capacity:
        raise ValidationError("ظرفیت کلاس تکمیل است.")


@transaction.atomic
def create_enrollment(**validated_data):
    class_section = _locked_class(validated_data["class_section"])
    _ensure_capacity(class_section)
    validated_data["class_section"] = class_section
    enrollment = Enrollment(**validated_data)
    enrollment.full_clean()
    enrollment.save()
    return enrollment


@transaction.atomic
def change_class(*, enrollment, new_class, reason, actor):
    enrollment = _locked_enrollment(enrollment)
    if enrollment.status != Enrollment.Status.ACTIVE:
        raise ValidationError("فقط ثبت‌نام فعال قابل تغییر کلاس است.")
    if new_class.pk == enrollment.class_section_id:
        raise ValidationError("کلاس جدید با کلاس فعلی یکسان است.")
    new_class = _locked_class(new_class)
    if new_class.school_id != enrollment.school_id:
        raise ValidationError("برای تغییر شعبه از عملیات انتقال استفاده کنید.")
    if new_class.academic_year_id != enrollment.academic_year_id:
        raise ValidationError("سال تحصیلی کلاس جدید متفاوت است.")
    if new_class.grade_level_id != enrollment.grade_level_id:
        raise ValidationError("پایه کلاس جدید متفاوت است.")
    _ensure_capacity(new_class)
    old_class_id = enrollment.class_section_id
    enrollment.class_section = new_class
    enrollment.full_clean()
    enrollment.save(update_fields=["class_section", "updated_at"])
    EnrollmentEvent.objects.create(
        enrollment=enrollment,
        event_type=EnrollmentEvent.EventType.CLASS_CHANGED,
        from_class_id=old_class_id,
        to_class_id=new_class.id,
        reason=reason,
        actor=actor,
    )
    return enrollment


@transaction.atomic
def transfer_enrollment(
    *, enrollment, school, grade_level, class_section, student_number, transfer_date, reason, actor
):
    enrollment = _locked_enrollment(enrollment)
    if enrollment.status != Enrollment.Status.ACTIVE:
        raise ValidationError("ثبت‌نام مبدأ فعال نیست.")
    if transfer_date < enrollment.enrolled_on:
        raise ValidationError({"transfer_date": "تاریخ انتقال قبل از تاریخ ثبت‌نام است."})
    if school.pk == enrollment.school_id:
        raise ValidationError("برای جابه‌جایی داخل یک شعبه از تغییر کلاس استفاده کنید.")
    class_section = _locked_class(class_section)
    if school.organization_id != enrollment.student.organization_id:
        raise ValidationError("شعبه مقصد متعلق به مجموعه دانش‌آموز نیست.")
    if class_section.school_id != school.id:
        raise ValidationError("کلاس مقصد متعلق به شعبه مقصد نیست.")
    if class_section.academic_year_id != enrollment.academic_year_id:
        raise ValidationError("سال تحصیلی کلاس مقصد متفاوت است.")
    if class_section.grade_level_id != grade_level.id:
        raise ValidationError("پایه کلاس مقصد متفاوت است.")
    _ensure_capacity(class_section)

    enrollment.status = Enrollment.Status.TRANSFERRED
    enrollment.left_on = transfer_date
    enrollment.full_clean()
    enrollment.save(update_fields=["status", "left_on", "updated_at"])
    EnrollmentEvent.objects.create(
        enrollment=enrollment,
        event_type=EnrollmentEvent.EventType.TRANSFER_OUT,
        from_class_id=enrollment.class_section_id,
        previous_status=Enrollment.Status.ACTIVE,
        new_status=Enrollment.Status.TRANSFERRED,
        reason=reason,
        actor=actor,
    )
    target = Enrollment(
        student=enrollment.student,
        school=school,
        academic_year=enrollment.academic_year,
        grade_level=grade_level,
        class_section=class_section,
        student_number=student_number,
        status=Enrollment.Status.ACTIVE,
        enrolled_on=transfer_date,
    )
    target.full_clean()
    target.save()
    EnrollmentEvent.objects.create(
        enrollment=target,
        event_type=EnrollmentEvent.EventType.TRANSFER_IN,
        to_class_id=class_section.id,
        previous_status=Enrollment.Status.TRANSFERRED,
        new_status=Enrollment.Status.ACTIVE,
        reason=reason,
        actor=actor,
    )
    return target


@transaction.atomic
def change_status(*, enrollment, new_status, date, reason, actor):
    enrollment = _locked_enrollment(enrollment)
    if enrollment.status != Enrollment.Status.ACTIVE:
        raise ValidationError("فقط ثبت‌نام فعال قابل خاتمه است.")
    if date < enrollment.enrolled_on:
        raise ValidationError({"date": "تاریخ خاتمه قبل از تاریخ ثبت‌نام است."})
    old_status = enrollment.status
    enrollment.status = new_status
    enrollment.left_on = date
    enrollment.full_clean()
    enrollment.save(update_fields=["status", "left_on", "updated_at"])
    EnrollmentEvent.objects.create(
        enrollment=enrollment,
        event_type=EnrollmentEvent.EventType.STATUS_CHANGED,
        from_class_id=enrollment.class_section_id,
        previous_status=old_status,
        new_status=new_status,
        reason=reason,
        actor=actor,
    )
    return enrollment
