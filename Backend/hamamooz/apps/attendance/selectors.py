from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Q
from django.utils import timezone

from hamamooz.apps.accounts.access import allowed_class_ids, selected_school_ids
from hamamooz.apps.students.models import Enrollment

from .models import AttendancePolicy, AttendanceRecord, AttendanceSession

ABSENT_STATUSES = [
    AttendanceRecord.Status.ABSENT_EXCUSED,
    AttendanceRecord.Status.ABSENT_UNEXCUSED,
]


def scoped_session_queryset(request):
    school_ids = selected_school_ids(request)
    class_ids = allowed_class_ids(request.user, school_ids)
    return AttendanceSession.objects.filter(
        school_id__in=school_ids,
        class_section_id__in=class_ids,
    ).select_related(
        "school",
        "academic_year",
        "class_section__grade_level",
        "term",
        "course_offering__grade_subject__subject",
        "course_offering__teacher",
        "taken_by",
        "finalized_by",
    )


def scoped_record_queryset(request):
    school_ids = selected_school_ids(request)
    class_ids = allowed_class_ids(request.user, school_ids)
    return (
        AttendanceRecord.objects.filter(
            session__school_id__in=school_ids,
            session__class_section_id__in=class_ids,
            session__is_deleted=False,
            session__status__in=[
                AttendanceSession.Status.DRAFT,
                AttendanceSession.Status.FINALIZED,
            ],
        )
        .select_related(
            "session__school",
            "session__academic_year",
            "session__class_section",
            "session__course_offering__grade_subject__subject",
            "enrollment__student",
            "enrollment__school",
            "enrollment__class_section",
            "recorded_by",
            "excuse_submitted_by",
            "reviewed_by",
        )
        .prefetch_related("evidence_files", "history")
    )


def attendance_date_range(*, academic_year, date_from=None, date_to=None, lookback_days=None):
    today = timezone.localdate()
    requested_end = date_to or today
    end = min(max(requested_end, academic_year.starts_on), academic_year.ends_on)
    if date_from:
        start = max(date_from, academic_year.starts_on)
    elif lookback_days:
        start = max(end - timedelta(days=lookback_days - 1), academic_year.starts_on)
    else:
        start = academic_year.starts_on
    return min(start, end), end


def report_records(*, date_from, date_to, scope=None):
    queryset = AttendanceRecord.objects.filter(
        session__status=AttendanceSession.Status.FINALIZED,
        session__is_deleted=False,
        session__session_date__range=(date_from, date_to),
    )
    if scope:
        queryset = queryset.filter(session__scope=scope)
    return queryset


def enrollment_metrics_map(*, enrollment_ids, date_from, date_to, scope=None, include_excused=True):
    enrollment_ids = list(enrollment_ids)
    if not enrollment_ids:
        return {}
    absent_statuses = [AttendanceRecord.Status.ABSENT_UNEXCUSED]
    if include_excused:
        absent_statuses.append(AttendanceRecord.Status.ABSENT_EXCUSED)
    rows = (
        report_records(date_from=date_from, date_to=date_to, scope=scope)
        .filter(enrollment_id__in=enrollment_ids)
        .values("enrollment_id")
        .annotate(
            total=Count("id"),
            absent=Count("id", filter=Q(status__in=absent_statuses)),
            excused=Count("id", filter=Q(status=AttendanceRecord.Status.ABSENT_EXCUSED)),
            unexcused=Count("id", filter=Q(status=AttendanceRecord.Status.ABSENT_UNEXCUSED)),
            late=Count("id", filter=Q(late_minutes__gt=0)),
            early_leave=Count("id", filter=Q(early_leave_minutes__gt=0)),
        )
    )
    results = {}
    for row in rows:
        total = row["total"] or 0
        absent = row["absent"] or 0
        percent = Decimal("0.00")
        if total:
            percent = (Decimal(absent) * Decimal("100") / Decimal(total)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        results[row["enrollment_id"]] = {
            "total_sessions": total,
            "absence_count": absent,
            "excused_absence_count": row["excused"] or 0,
            "unexcused_absence_count": row["unexcused"] or 0,
            "late_count": row["late"] or 0,
            "early_leave_count": row["early_leave"] or 0,
            "absence_percent": percent,
        }
    empty = {
        "total_sessions": 0,
        "absence_count": 0,
        "excused_absence_count": 0,
        "unexcused_absence_count": 0,
        "late_count": 0,
        "early_leave_count": 0,
        "absence_percent": Decimal("0.00"),
    }
    return {
        enrollment_id: results.get(enrollment_id, empty.copy()) for enrollment_id in enrollment_ids
    }


def enrollment_metrics(*, enrollment, date_from, date_to, scope=None, include_excused=True):
    return enrollment_metrics_map(
        enrollment_ids=[enrollment.id],
        date_from=date_from,
        date_to=date_to,
        scope=scope,
        include_excused=include_excused,
    )[enrollment.id]


def active_enrollments_for_class(session):
    return (
        Enrollment.all_objects.filter(
            school=session.school,
            academic_year=session.academic_year,
            class_section=session.class_section,
            enrolled_on__lte=session.session_date,
            is_deleted=False,
        )
        .filter(Q(left_on__isnull=True) | Q(left_on__gte=session.session_date))
        .select_related("student", "school", "academic_year", "grade_level", "class_section")
    )


def policy_for_session(session):
    return AttendancePolicy.objects.filter(
        school=session.school,
        academic_year=session.academic_year,
        is_active=True,
    ).first()
