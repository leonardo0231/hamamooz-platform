from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from hamamooz.apps.organizations.models import ClassSection

from .models import Enrollment, EnrollmentEvent, Student


def _locked_enrollment(enrollment):
    return (
        Enrollment.objects.select_for_update(of=("self",))
        .select_related("student", "school", "academic_year", "grade_level", "class_section")
        .get(pk=enrollment.pk)
    )


def _locked_class(class_section):
    return (
        ClassSection.objects.select_for_update(of=("self",))
        .select_related("school", "academic_year", "grade_level")
        .get(pk=class_section.pk)
    )


def _ensure_capacity(class_section):
    active_count = Enrollment.objects.filter(
        class_section=class_section, status=Enrollment.Status.ACTIVE
    ).count()
    if active_count >= class_section.capacity:
        raise ValidationError("ظرفیت کلاس تکمیل است.")


def _sync_student_status(student):
    if Enrollment.objects.filter(student=student, status=Enrollment.Status.ACTIVE).exists():
        desired = Student.Status.ACTIVE
    else:
        latest = (
            Enrollment.all_objects.filter(student=student, is_deleted=False)
            .order_by("-left_on", "-updated_at")
            .first()
        )
        mapping = {
            Enrollment.Status.GRADUATED: Student.Status.GRADUATED,
            Enrollment.Status.WITHDRAWN: Student.Status.WITHDRAWN,
            Enrollment.Status.TRANSFERRED: Student.Status.TRANSFERRED,
        }
        desired = mapping.get(getattr(latest, "status", None), student.status)
    if student.status != desired:
        student.status = desired
        student.save(update_fields=["status", "updated_at"])


@transaction.atomic
def create_enrollment(**validated_data):
    class_section = _locked_class(validated_data["class_section"])
    _ensure_capacity(class_section)
    validated_data["class_section"] = class_section
    enrollment = Enrollment(**validated_data)
    enrollment.full_clean()
    enrollment.save()
    _sync_student_status(enrollment.student)
    return enrollment


@transaction.atomic
def change_class(*, enrollment, new_class, reason, actor, effective_date=None):
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

    effective_date = effective_date or max(timezone.localdate(), enrollment.enrolled_on)
    if effective_date < enrollment.enrolled_on:
        raise ValidationError({"effective_date": "تاریخ تغییر کلاس قبل از شروع ثبت‌نام است."})
    if not (
        enrollment.academic_year.starts_on <= effective_date <= enrollment.academic_year.ends_on
    ):
        raise ValidationError({"effective_date": "تاریخ تغییر کلاس خارج از سال تحصیلی است."})

    old_class_id = enrollment.class_section_id
    # If no historical period exists, mutating the newly-created enrollment is safe.
    if effective_date == enrollment.enrolled_on:
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

    enrollment.status = Enrollment.Status.TRANSFERRED
    enrollment.left_on = effective_date - timedelta(days=1)
    enrollment.full_clean()
    enrollment.save(update_fields=["status", "left_on", "updated_at"])
    EnrollmentEvent.objects.create(
        enrollment=enrollment,
        event_type=EnrollmentEvent.EventType.CLASS_CHANGED,
        from_class_id=old_class_id,
        to_class_id=new_class.id,
        previous_status=Enrollment.Status.ACTIVE,
        new_status=Enrollment.Status.TRANSFERRED,
        reason=reason,
        actor=actor,
    )

    target = Enrollment(
        student=enrollment.student,
        school=enrollment.school,
        academic_year=enrollment.academic_year,
        grade_level=enrollment.grade_level,
        class_section=new_class,
        student_number=enrollment.student_number,
        status=Enrollment.Status.ACTIVE,
        enrolled_on=effective_date,
    )
    target.full_clean()
    target.save()
    EnrollmentEvent.objects.create(
        enrollment=target,
        event_type=EnrollmentEvent.EventType.CLASS_CHANGED,
        from_class_id=old_class_id,
        to_class_id=new_class.id,
        previous_status=Enrollment.Status.TRANSFERRED,
        new_status=Enrollment.Status.ACTIVE,
        reason=reason,
        actor=actor,
    )
    _sync_student_status(target.student)
    return target


@transaction.atomic
def transfer_enrollment(
    *, enrollment, school, grade_level, class_section, student_number, transfer_date, reason, actor
):
    enrollment = _locked_enrollment(enrollment)
    if enrollment.status != Enrollment.Status.ACTIVE:
        raise ValidationError("ثبت‌نام مبدأ فعال نیست.")
    if transfer_date <= enrollment.enrolled_on:
        raise ValidationError({"transfer_date": "تاریخ انتقال باید بعد از تاریخ ثبت‌نام باشد."})
    if not (
        enrollment.academic_year.starts_on <= transfer_date <= enrollment.academic_year.ends_on
    ):
        raise ValidationError({"transfer_date": "تاریخ انتقال خارج از سال تحصیلی است."})
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
    enrollment.left_on = transfer_date - timedelta(days=1)
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
    _sync_student_status(target.student)
    return target


@transaction.atomic
def change_status(*, enrollment, new_status, date, reason, actor):
    enrollment = _locked_enrollment(enrollment)
    if enrollment.status != Enrollment.Status.ACTIVE:
        raise ValidationError("فقط ثبت‌نام فعال قابل خاتمه است.")
    if date < enrollment.enrolled_on:
        raise ValidationError({"date": "تاریخ خاتمه قبل از تاریخ ثبت‌نام است."})
    if not (enrollment.academic_year.starts_on <= date <= enrollment.academic_year.ends_on):
        raise ValidationError({"date": "تاریخ خاتمه خارج از سال تحصیلی است."})
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
    _sync_student_status(enrollment.student)
    return enrollment
