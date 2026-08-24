from decimal import Decimal, ROUND_HALF_UP

from rest_framework.exceptions import ValidationError

from .models import (
    SummerComprehensiveExam,
    SummerCourseRegistration,
    SummerRegistration,
    SummerSubjectScore,
)


def _resolve_exam(registration, exam=None):
    if exam is not None:
        if exam.program_id != registration.program_id:
            raise ValidationError({"exam": "آزمون متعلق به برنامه این ثبت‌نام نیست."})
        return exam
    try:
        return registration.program.exams.get()
    except SummerComprehensiveExam.DoesNotExist as exc:
        raise ValidationError({"exam": "برای برنامه تابستانی آزمون جامع تعریف نشده است."}) from exc
    except SummerComprehensiveExam.MultipleObjectsReturned as exc:
        raise ValidationError({"exam": "آزمون جامع برنامه تابستانی یکتا نیست."}) from exc


def _registration_components(registration, exam):
    if registration.is_deleted:
        raise ValidationError({"registration": "ثبت‌نام تابستانی فعال نیست."})
    if exam.is_deleted:
        raise ValidationError({"exam": "آزمون جامع فعال نیست."})
    course_registrations = list(
        SummerCourseRegistration.objects.filter(registration=registration)
        .select_related("course__subject", "registration__enrollment")
        .order_by("course__subject__title")
    )
    if not course_registrations:
        raise ValidationError(
            {"courses": "برای این ثبت‌نام تابستانی هیچ درس فعالی انتخاب نشده است."}
        )
    invalid = [
        item.id
        for item in course_registrations
        if item.course.program_id != registration.program_id
    ]
    if invalid:
        raise ValidationError({"courses": "درس‌های ثبت‌نام‌شده با برنامه تابستانی سازگار نیستند."})
    scores = {
        item.course_registration_id: item
        for item in SummerSubjectScore.objects.filter(
            exam=exam, course_registration__in=course_registrations
        ).select_related("course_registration__course__subject")
    }
    missing = [item.id for item in course_registrations if item.id not in scores]
    if missing:
        raise ValidationError(
            {
                "scores": (
                    "نمرات آزمون جامع برای این ثبت‌نام ناقص است. "
                    f"درس‌های انتخابی: {len(course_registrations)}، نمرات معتبر: {len(scores)}."
                )
            }
        )
    return course_registrations, scores


def validate_summer_report_readiness(registration, exam=None):
    """Validate authoritative summer inputs before an official report transition."""

    if not isinstance(registration, SummerRegistration):
        raise ValidationError({"registration": "ثبت‌نام تابستانی معتبر نیست."})
    resolved_exam = _resolve_exam(registration, exam)
    if resolved_exam.status != SummerComprehensiveExam.Status.FINALIZED:
        raise ValidationError({"exam": "آزمون جامع برای صدور رسمی باید نهایی شده باشد."})
    if resolved_exam.finalized_at is None or resolved_exam.finalized_by_id is None:
        raise ValidationError(
            {"exam": "زمان و مسئول نهایی‌سازی آزمون جامع برای صدور رسمی معتبر نیست."}
        )
    _registration_components(registration, resolved_exam)
    return resolved_exam


def validate_exam_completeness(exam):
    """Validate all active registrations before finalizing a comprehensive exam."""

    registrations = list(
        SummerRegistration.objects.filter(program=exam.program).select_related(
            "program", "enrollment__student"
        )
    )
    if not registrations:
        raise ValidationError(
            {"registrations": "برای نهایی‌سازی آزمون، حداقل یک ثبت‌نام تابستانی لازم است."}
        )
    for registration in registrations:
        _registration_components(registration, exam)
    return registrations


def summer_registration_result(registration, exam=None):
    """Return a direct-score result without persisting questions, attempts, or ranks."""

    resolved_exam = validate_summer_report_readiness(registration, exam)
    course_registrations, scores = _registration_components(registration, resolved_exam)
    weighted_total = Decimal("0")
    coefficient_total = Decimal("0")
    courses = []
    for item in course_registrations:
        coefficient = item.course.subject.default_coefficient
        if coefficient <= 0:
            raise ValidationError(
                {"courses": f"ضریب درس {item.course.subject.title} باید بزرگ‌تر از صفر باشد."}
            )
        score = scores[item.id].value
        weighted_total += score * coefficient
        coefficient_total += coefficient
        courses.append(
            {
                "course_registration_id": str(item.id),
                "subject_id": str(item.course.subject_id),
                "subject_title": item.course.subject.title,
                "coefficient": coefficient,
                "score": score,
            }
        )
    average = (weighted_total / coefficient_total).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    threshold = registration.program.pass_threshold
    return {
        "program_id": str(registration.program_id),
        "registration_id": str(registration.id),
        "enrollment_id": str(registration.enrollment_id),
        "exam_id": str(resolved_exam.id),
        "courses": courses,
        "average": average,
        "pass_threshold": threshold,
        "passed": None if threshold is None else average >= threshold,
    }
