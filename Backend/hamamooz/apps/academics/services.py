from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from hamamooz.apps.students.models import Enrollment

from .models import Assessment, Score, ScoreRevision


def _lock_assessment(assessment):
    return (
        Assessment.objects.select_for_update(of=("self",))
        .select_related("course_offering__class_section")
        .get(pk=assessment.pk)
    )


def validate_score_completeness(assessment):
    assessment_date = assessment.assessment_date
    active_enrollment_ids = set(
        Enrollment.all_objects.filter(
            class_section=assessment.course_offering.class_section,
            enrolled_on__lte=assessment_date,
            is_deleted=False,
        )
        .filter(Q(left_on__isnull=True) | Q(left_on__gte=assessment_date))
        .values_list("id", flat=True)
    )
    entered_enrollment_ids = set(
        assessment.scores.exclude(status=Score.Status.NOT_ENTERED).values_list(
            "enrollment_id", flat=True
        )
    )
    missing = active_enrollment_ids - entered_enrollment_ids
    unexpected = entered_enrollment_ids - active_enrollment_ids
    if not active_enrollment_ids or missing or unexpected:
        raise ValidationError(
            {
                "scores": (
                    "نمرات با فهرست فعلی دانش‌آموزان فعال منطبق نیست. "
                    f"فعال: {len(active_enrollment_ids)}، ثبت‌شده معتبر: "
                    f"{len(active_enrollment_ids & entered_enrollment_ids)}، "
                    f"فاقد نمره: {len(missing)}، خارج از فهرست فعال: {len(unexpected)}."
                )
            }
        )


def _transition(assessment, *, allowed, target, actor, reason=""):
    if assessment.status not in allowed:
        raise ValidationError(
            f"انتقال از وضعیت {assessment.get_status_display()} به وضعیت درخواستی مجاز نیست."
        )
    assessment.status = target
    assessment.workflow_version += 1
    if target == Assessment.Status.SUBMITTED:
        assessment.submitted_at = timezone.now()
        assessment.rejection_reason = ""
    elif target in {Assessment.Status.REJECTED, Assessment.Status.APPROVED}:
        assessment.reviewed_at = timezone.now()
        assessment.reviewed_by = actor
        assessment.rejection_reason = reason if target == Assessment.Status.REJECTED else ""
    elif target == Assessment.Status.LOCKED:
        assessment.locked_at = timezone.now()
        assessment.reviewed_by = actor
    assessment.save()
    return assessment


@transaction.atomic
def submit_assessment(assessment, actor):
    assessment = _lock_assessment(assessment)
    validate_score_completeness(assessment)
    return _transition(
        assessment,
        allowed=[Assessment.Status.DRAFT, Assessment.Status.REJECTED],
        target=Assessment.Status.SUBMITTED,
        actor=actor,
    )


@transaction.atomic
def approve_assessment(assessment, actor):
    assessment = _lock_assessment(assessment)
    return _transition(
        assessment,
        allowed=[Assessment.Status.SUBMITTED],
        target=Assessment.Status.APPROVED,
        actor=actor,
    )


@transaction.atomic
def reject_assessment(assessment, actor, reason):
    assessment = _lock_assessment(assessment)
    if not reason.strip():
        raise ValidationError({"reason": "دلیل رد الزامی است."})
    return _transition(
        assessment,
        allowed=[Assessment.Status.SUBMITTED],
        target=Assessment.Status.REJECTED,
        actor=actor,
        reason=reason,
    )


@transaction.atomic
def lock_assessment(assessment, actor):
    assessment = _lock_assessment(assessment)
    validate_score_completeness(assessment)
    return _transition(
        assessment,
        allowed=[Assessment.Status.APPROVED],
        target=Assessment.Status.LOCKED,
        actor=actor,
    )


def _write_score(*, assessment, enrollment, value, status, note, actor, reason=""):
    score = (
        Score.objects.select_for_update()
        .filter(assessment=assessment, enrollment=enrollment)
        .first()
    )
    old = {
        "value": score.value if score else None,
        "status": score.status if score else "",
        "note": score.note if score else "",
    }
    if score is None:
        score = Score(assessment=assessment, enrollment=enrollment, recorded_by=actor)
    else:
        score.revision += 1
    score.value = value
    score.status = status
    score.note = note
    score.recorded_by = actor
    score.full_clean()
    score.save()
    ScoreRevision.objects.create(
        score=score,
        old_value=old["value"],
        new_value=score.value,
        old_status=old["status"],
        new_status=score.status,
        old_note=old["note"],
        new_note=score.note,
        reason=reason,
        changed_by=actor,
        assessment_status=assessment.status,
    )
    return score


@transaction.atomic
def bulk_upsert_scores(*, assessment, entries, actor):
    assessment = _lock_assessment(assessment)
    if assessment.status not in [Assessment.Status.DRAFT, Assessment.Status.REJECTED]:
        raise ValidationError("نمرات فقط در وضعیت پیش‌نویس یا ردشده قابل ویرایش‌اند.")
    results = []
    seen = set()
    for entry in entries:
        enrollment = entry["enrollment"]
        if enrollment.id in seen:
            raise ValidationError({"entries": "یک دانش‌آموز بیش از یک بار ارسال شده است."})
        seen.add(enrollment.id)
        if enrollment.class_section_id != assessment.course_offering.class_section_id:
            raise ValidationError({"entries": f"دانش‌آموز {enrollment.id} عضو این کلاس نیست."})
        assessment_date = assessment.assessment_date
        if enrollment.enrolled_on > assessment_date or (
            enrollment.left_on is not None and enrollment.left_on < assessment_date
        ):
            raise ValidationError(
                {"entries": f"ثبت‌نام دانش‌آموز {enrollment.id} در تاریخ ارزیابی فعال نبوده است."}
            )
        results.append(
            _write_score(
                assessment=assessment,
                enrollment=enrollment,
                value=entry.get("value"),
                status=entry["status"],
                note=entry.get("note", ""),
                actor=actor,
            )
        )
    return results


@transaction.atomic
def correct_locked_score(*, score, value, status, note, reason, actor):
    assessment = _lock_assessment(score.assessment)
    score = (
        Score.objects.select_for_update(of=("self",))
        .select_related("enrollment")
        .get(pk=score.pk)
    )
    if assessment.status != Assessment.Status.LOCKED:
        raise ValidationError("این عملیات فقط برای نمره قفل‌شده است.")
    if len(reason.strip()) < 5:
        raise ValidationError({"reason": "دلیل اصلاح نمره قفل‌شده باید حداقل ۵ نویسه باشد."})
    return _write_score(
        assessment=assessment,
        enrollment=score.enrollment,
        value=value,
        status=status,
        note=note,
        actor=actor,
        reason=reason,
    )
