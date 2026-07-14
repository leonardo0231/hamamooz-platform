from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import Enrollment, EnrollmentEvent


@transaction.atomic
def change_class(*, enrollment, new_class, reason, actor):
    if enrollment.status != Enrollment.Status.ACTIVE:
        raise ValidationError("فقط ثبت‌نام فعال قابل تغییر کلاس است.")
    if new_class.school_id != enrollment.school_id:
        raise ValidationError("برای تغییر شعبه از عملیات انتقال استفاده کنید.")
    if new_class.academic_year_id != enrollment.academic_year_id:
        raise ValidationError("سال تحصیلی کلاس جدید متفاوت است.")
    if new_class.grade_level_id != enrollment.grade_level_id:
        raise ValidationError("پایه کلاس جدید متفاوت است.")
    if (
        Enrollment.objects.select_for_update()
        .filter(class_section=new_class, status=Enrollment.Status.ACTIVE)
        .count()
        >= new_class.capacity
    ):
        raise ValidationError("ظرفیت کلاس جدید تکمیل است.")
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
    if enrollment.status != Enrollment.Status.ACTIVE:
        raise ValidationError("ثبت‌نام مبدأ فعال نیست.")
    if school.organization_id != enrollment.student.organization_id:
        raise ValidationError("شعبه مقصد متعلق به مجموعه دانش‌آموز نیست.")
    if class_section.school_id != school.id:
        raise ValidationError("کلاس مقصد متعلق به شعبه مقصد نیست.")
    if class_section.academic_year_id != enrollment.academic_year_id:
        raise ValidationError("سال تحصیلی کلاس مقصد متفاوت است.")
    if class_section.grade_level_id != grade_level.id:
        raise ValidationError("پایه کلاس مقصد متفاوت است.")
    if (
        Enrollment.objects.select_for_update()
        .filter(class_section=class_section, status=Enrollment.Status.ACTIVE)
        .count()
        >= class_section.capacity
    ):
        raise ValidationError("ظرفیت کلاس مقصد تکمیل است.")

    enrollment.status = Enrollment.Status.TRANSFERRED
    enrollment.left_on = transfer_date
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
    if enrollment.status != Enrollment.Status.ACTIVE:
        raise ValidationError("فقط ثبت‌نام فعال قابل خاتمه است.")
    old_status = enrollment.status
    enrollment.status = new_status
    enrollment.left_on = date
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
