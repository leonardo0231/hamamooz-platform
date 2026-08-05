from datetime import datetime
from hashlib import sha256

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from hamamooz.apps.core.services import record_audit
from hamamooz.apps.students.models import Enrollment, StudentGuardian

from .models import (
    AbsenceEvidence,
    AttendanceAlert,
    AttendancePolicy,
    AttendanceRecord,
    AttendanceRecordRevision,
    AttendanceSession,
    ParentNotification,
)
from .permissions import can_manage_session
from .selectors import (
    active_enrollments_for_class,
    attendance_date_range,
    enrollment_metrics,
    enrollment_metrics_map,
)

RECORD_SNAPSHOT_FIELDS = [
    "status",
    "arrival_time",
    "departure_time",
    "late_minutes",
    "early_leave_minutes",
    "note",
    "absence_reason",
    "excuse_status",
    "review_note",
    "revision",
]


def _serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def record_snapshot(record):
    return {field: _serialize_value(getattr(record, field)) for field in RECORD_SNAPSHOT_FIELDS}


def _minutes_between(start, end):
    start_dt = datetime.combine(timezone.localdate(), start)
    end_dt = datetime.combine(timezone.localdate(), end)
    return max(0, int((end_dt - start_dt).total_seconds() // 60))


def _timing_values(session, item):
    status = item.get("status", AttendanceRecord.Status.PRESENT)
    if status != AttendanceRecord.Status.PRESENT:
        return {
            "arrival_time": None,
            "departure_time": None,
            "late_minutes": 0,
            "early_leave_minutes": 0,
        }

    arrival = item.get("arrival_time")
    departure = item.get("departure_time")
    late_minutes = item.get("late_minutes", 0)
    early_leave_minutes = item.get("early_leave_minutes", 0)
    if arrival and session.starts_at:
        late_minutes = _minutes_between(session.starts_at, arrival)
    if departure and session.ends_at:
        early_leave_minutes = _minutes_between(departure, session.ends_at)
    return {
        "arrival_time": arrival,
        "departure_time": departure,
        "late_minutes": late_minutes,
        "early_leave_minutes": early_leave_minutes,
    }


def _validate_session_writer(*, session, actor):
    if not can_manage_session(actor, session):
        raise ValidationError("برای ثبت حضور و غیاب این جلسه دسترسی ندارید.")
    if session.status != AttendanceSession.Status.DRAFT:
        raise ValidationError("فقط جلسه پیش‌نویس قابل ویرایش است.")


@transaction.atomic
def bulk_record_attendance(*, session, items, actor, request=None):
    session = (
        AttendanceSession.all_objects.select_for_update(of=("self",))
        .select_related("school", "academic_year", "class_section", "course_offering")
        .get(pk=session.pk)
    )
    _validate_session_writer(session=session, actor=actor)

    enrollment_ids = [item["enrollment"].id for item in items]
    if len(enrollment_ids) != len(set(enrollment_ids)):
        raise ValidationError("هر دانش‌آموز در یک درخواست فقط یک بار قابل ثبت است.")

    valid_enrollments = {
        enrollment.id: enrollment
        for enrollment in active_enrollments_for_class(session).filter(id__in=enrollment_ids)
    }
    invalid_ids = set(enrollment_ids) - set(valid_enrollments)
    if invalid_ids:
        raise ValidationError(
            {"records": f"ثبت‌نام‌های نامعتبر یا خارج از کلاس: {', '.join(map(str, invalid_ids))}"}
        )

    existing = {
        record.enrollment_id: record
        for record in AttendanceRecord.all_objects.select_for_update().filter(
            session=session, enrollment_id__in=enrollment_ids
        )
    }
    saved = []
    created_count = 0
    updated_count = 0
    for item in items:
        enrollment = valid_enrollments[item["enrollment"].id]
        record = existing.get(enrollment.id)
        created = record is None
        if created:
            record = AttendanceRecord(session=session, enrollment=enrollment, recorded_by=actor)
            before = None
        else:
            before = record_snapshot(record)
            if record.excuse_status != AttendanceRecord.ExcuseStatus.NOT_REQUIRED:
                raise ValidationError(
                    {
                        "records": (
                            f"رکورد ثبت‌نام {enrollment.id} دارای گردش‌کار توجیه غیبت است؛ "
                            "اصلاح آن را از عملیات اختصاصی رکورد انجام دهید."
                        )
                    }
                )
            if record.is_deleted:
                record.is_deleted = False
                record.deleted_at = None

        record.status = item.get("status", AttendanceRecord.Status.PRESENT)
        for field, value in _timing_values(session, item).items():
            setattr(record, field, value)
        record.note = item.get("note", "")
        record.absence_reason = ""
        record.excuse_status = AttendanceRecord.ExcuseStatus.NOT_REQUIRED
        record.excuse_submitted_by = None
        record.excuse_submitted_at = None
        record.reviewed_by = None
        record.reviewed_at = None
        record.review_note = ""
        record.recorded_by = actor
        if not created:
            record.revision += 1
        record.full_clean(exclude=["id"])
        record.save()
        after = record_snapshot(record)
        if created:
            created_count += 1
        else:
            updated_count += 1
            AttendanceRecordRevision.objects.create(
                attendance_record=record,
                changed_by=actor,
                reason="اصلاح از طریق ثبت گروهی حضور و غیاب",
                before=before,
                after=after,
            )
        saved.append(record)

    record_audit(
        action="attendance.records_bulk_saved",
        actor=actor,
        request=request,
        entity=session,
        organization_id=session.organization_id,
        school_id=session.school_id,
        changes={
            "created": created_count,
            "updated": updated_count,
            "record_ids": [str(record.id) for record in saved],
        },
    )
    return saved


@transaction.atomic
def correct_attendance_record(*, record, data, reason, actor, request=None):
    record = (
        AttendanceRecord.all_objects.select_for_update(of=("self", "session"))
        .select_related(
            "session__school",
            "session__academic_year",
            "session__class_section",
            "session__course_offering",
            "enrollment",
        )
        .get(pk=record.pk)
    )
    if not can_manage_session(actor, record.session):
        raise ValidationError("برای اصلاح این رکورد دسترسی ندارید.")
    before = record_snapshot(record)
    for field in [
        "status",
        "arrival_time",
        "departure_time",
        "late_minutes",
        "early_leave_minutes",
        "note",
    ]:
        if field in data:
            setattr(record, field, data[field])
    timing = _timing_values(
        record.session,
        {
            "status": record.status,
            "arrival_time": record.arrival_time,
            "departure_time": record.departure_time,
            "late_minutes": record.late_minutes,
            "early_leave_minutes": record.early_leave_minutes,
        },
    )
    for field, value in timing.items():
        setattr(record, field, value)
    if record.status == AttendanceRecord.Status.PRESENT:
        record.absence_reason = ""
        record.excuse_status = AttendanceRecord.ExcuseStatus.NOT_REQUIRED
        record.excuse_submitted_by = None
        record.excuse_submitted_at = None
        record.reviewed_by = None
        record.reviewed_at = None
        record.review_note = ""
    else:
        record.absence_reason = ""
        record.excuse_status = AttendanceRecord.ExcuseStatus.NOT_REQUIRED
        record.excuse_submitted_by = None
        record.excuse_submitted_at = None
        record.reviewed_by = None
        record.reviewed_at = None
        record.review_note = ""
    record.recorded_by = actor
    record.revision += 1
    record.full_clean(exclude=["id"])
    record.save()
    after = record_snapshot(record)
    AttendanceRecordRevision.objects.create(
        attendance_record=record,
        changed_by=actor,
        reason=reason,
        before=before,
        after=after,
    )
    record_audit(
        action="attendance.record_corrected",
        actor=actor,
        request=request,
        entity=record,
        organization_id=record.organization_id,
        school_id=record.school_id,
        changes={"before": before, "after": after, "reason": reason},
    )
    return record


@transaction.atomic
def finalize_attendance_session(*, session, actor, request=None):
    session = (
        AttendanceSession.all_objects.select_for_update(of=("self",))
        .select_related("school", "academic_year", "class_section", "course_offering")
        .get(pk=session.pk)
    )
    _validate_session_writer(session=session, actor=actor)
    expected_ids = set(active_enrollments_for_class(session).values_list("id", flat=True))
    recorded_ids = set(
        AttendanceRecord.objects.filter(session=session).values_list("enrollment_id", flat=True)
    )
    missing = expected_ids - recorded_ids
    extra = recorded_ids - expected_ids
    if missing or extra:
        raise ValidationError(
            {
                "records": {
                    "missing_enrollment_ids": [str(value) for value in sorted(missing, key=str)],
                    "invalid_enrollment_ids": [str(value) for value in sorted(extra, key=str)],
                }
            }
        )
    session.status = AttendanceSession.Status.FINALIZED
    session.finalized_by = actor
    session.finalized_at = timezone.now()
    session.full_clean(exclude=["id"])
    session.save(update_fields=["status", "finalized_by", "finalized_at", "updated_at"])
    record_audit(
        action="attendance.session_finalized",
        actor=actor,
        request=request,
        entity=session,
        organization_id=session.organization_id,
        school_id=session.school_id,
        changes={"record_count": len(recorded_ids)},
    )
    return session


@transaction.atomic
def cancel_attendance_session(*, session, actor, reason, request=None):
    session = (
        AttendanceSession.all_objects.select_for_update(of=("self",))
        .select_related("school", "academic_year", "class_section", "course_offering")
        .get(pk=session.pk)
    )
    _validate_session_writer(session=session, actor=actor)
    if session.status != AttendanceSession.Status.DRAFT:
        raise ValidationError("فقط جلسه پیش‌نویس قابل لغو است.")
    session.status = AttendanceSession.Status.CANCELLED
    session.notes = "\n".join(part for part in [session.notes, f"لغو: {reason}"] if part)
    session.save(update_fields=["status", "notes", "updated_at"])
    record_audit(
        action="attendance.session_cancelled",
        actor=actor,
        request=request,
        entity=session,
        organization_id=session.organization_id,
        school_id=session.school_id,
        changes={"reason": reason},
    )
    return session


@transaction.atomic
def submit_absence_excuse(*, record, reason, evidence_files, actor, request=None):
    record = (
        AttendanceRecord.all_objects.select_for_update(of=("self",))
        .select_related("session__school", "session__academic_year", "enrollment__student")
        .get(pk=record.pk)
    )
    if record.status == AttendanceRecord.Status.PRESENT:
        raise ValidationError("برای دانش‌آموز حاضر نمی‌توان درخواست توجیه غیبت ثبت کرد.")
    before = record_snapshot(record)
    record.status = AttendanceRecord.Status.ABSENT_UNEXCUSED
    record.absence_reason = reason
    record.excuse_status = AttendanceRecord.ExcuseStatus.PENDING
    record.excuse_submitted_by = actor
    record.excuse_submitted_at = timezone.now()
    record.reviewed_by = None
    record.reviewed_at = None
    record.review_note = ""
    record.revision += 1
    record.full_clean(exclude=["id"])
    record.save()

    evidence_objects = []
    for uploaded in evidence_files:
        evidence = AbsenceEvidence(
            attendance_record=record,
            file=uploaded,
            original_name=uploaded.name[:255],
            content_type=getattr(uploaded, "content_type", "")[:100],
            size_bytes=uploaded.size,
            uploaded_by=actor,
        )
        evidence.full_clean(exclude=["id"])
        evidence.save()
        evidence_objects.append(evidence)

    AttendanceRecordRevision.objects.create(
        attendance_record=record,
        changed_by=actor,
        reason="ثبت درخواست توجیه غیبت",
        before=before,
        after=record_snapshot(record),
    )
    record_audit(
        action="attendance.excuse_submitted",
        actor=actor,
        request=request,
        entity=record,
        organization_id=record.organization_id,
        school_id=record.school_id,
        changes={
            "evidence_ids": [str(item.id) for item in evidence_objects],
            "reason": reason,
        },
    )
    return record


@transaction.atomic
def review_absence_excuse(*, record, approved, note, actor, request=None):
    record = (
        AttendanceRecord.all_objects.select_for_update(of=("self",))
        .select_related("session__school", "session__academic_year", "enrollment__student")
        .prefetch_related("evidence_files")
        .get(pk=record.pk)
    )
    if record.excuse_status != AttendanceRecord.ExcuseStatus.PENDING:
        raise ValidationError("فقط درخواست در انتظار بررسی قابل تأیید یا رد است.")
    policy = AttendancePolicy.objects.filter(
        school_id=record.school_id,
        academic_year_id=record.session.academic_year_id,
        is_active=True,
    ).first()
    if (
        approved
        and policy
        and policy.require_evidence_for_excuse
        and not record.evidence_files.exists()
    ):
        raise ValidationError("طبق سیاست شعبه، تأیید غیبت موجه بدون مدرک مجاز نیست.")
    before = record_snapshot(record)
    record.reviewed_by = actor
    record.reviewed_at = timezone.now()
    record.review_note = note
    if approved:
        record.status = AttendanceRecord.Status.ABSENT_EXCUSED
        record.excuse_status = AttendanceRecord.ExcuseStatus.APPROVED
    else:
        record.status = AttendanceRecord.Status.ABSENT_UNEXCUSED
        record.excuse_status = AttendanceRecord.ExcuseStatus.REJECTED
    record.revision += 1
    record.full_clean(exclude=["id"])
    record.save()
    AttendanceRecordRevision.objects.create(
        attendance_record=record,
        changed_by=actor,
        reason="تأیید غیبت موجه" if approved else "رد درخواست توجیه غیبت",
        before=before,
        after=record_snapshot(record),
    )
    record_audit(
        action="attendance.excuse_approved" if approved else "attendance.excuse_rejected",
        actor=actor,
        request=request,
        entity=record,
        organization_id=record.organization_id,
        school_id=record.school_id,
        changes={"review_note": note},
    )
    return record


def _notification_recipient(guardian, channel):
    if channel == ParentNotification.Channel.EMAIL:
        return guardian.email
    if channel == ParentNotification.Channel.SMS:
        return guardian.phone_primary
    return str(guardian.id)


def _default_channels_for_guardian(guardian):
    channels = []
    if guardian.email:
        channels.append(ParentNotification.Channel.EMAIL)
    sms_backend = getattr(settings, "ATTENDANCE_SMS_BACKEND", "")
    if guardian.phone_primary and not sms_backend.endswith("DisabledSMSBackend"):
        channels.append(ParentNotification.Channel.SMS)
    return channels


def _notification_dedupe_key(*parts):
    raw = ":".join(str(part) for part in parts)
    return sha256(raw.encode("utf-8")).hexdigest()


def _schedule_notification(notification):
    if not getattr(settings, "ATTENDANCE_ASYNC_NOTIFICATIONS", True):
        from .notifications import dispatch_notification

        dispatch_notification(notification)
        notification.refresh_from_db()
        return notification
    from .tasks import dispatch_parent_notification

    transaction.on_commit(lambda: dispatch_parent_notification.delay(str(notification.id)))
    return notification


def _guardians_for_student(student):
    primary = StudentGuardian.objects.filter(student=student, is_primary=True).select_related(
        "guardian"
    )
    if primary.exists():
        return [link.guardian for link in primary]
    return [
        link.guardian
        for link in StudentGuardian.objects.filter(student=student).select_related("guardian")
    ]


@transaction.atomic
def queue_record_parent_notifications(*, record, channels=None, actor=None):
    record = AttendanceRecord.objects.select_related(
        "session__school", "session__academic_year", "enrollment__student"
    ).get(pk=record.pk)
    policy = AttendancePolicy.objects.filter(
        school=record.session.school,
        academic_year=record.session.academic_year,
        is_active=True,
    ).first()
    requested_channels = channels or (policy.notification_channels if policy else [])
    student = record.enrollment.student
    subject = f"گزارش حضور و غیاب {student.full_name}"
    message = (
        f"وضعیت {student.full_name} در تاریخ {record.session.session_date}: "
        f"{record.get_status_display()}."
    )
    if record.late_minutes:
        message += f" تأخیر: {record.late_minutes} دقیقه."
    if record.early_leave_minutes:
        message += f" خروج زودهنگام: {record.early_leave_minutes} دقیقه."
    if record.absence_reason:
        message += f" دلیل ثبت‌شده: {record.absence_reason}"

    notifications = []
    for guardian in _guardians_for_student(student):
        guardian_channels = requested_channels or _default_channels_for_guardian(guardian)
        for channel in guardian_channels:
            dedupe_key = _notification_dedupe_key(
                "record", record.id, record.revision, guardian.id, channel
            )
            notification, created = ParentNotification.objects.get_or_create(
                dedupe_key=dedupe_key,
                defaults={
                    "school": record.session.school,
                    "student": student,
                    "enrollment": record.enrollment,
                    "guardian": guardian,
                    "attendance_record": record,
                    "kind": ParentNotification.Kind.ABSENCE,
                    "channel": channel,
                    "recipient": _notification_recipient(guardian, channel),
                    "subject": subject,
                    "message": message,
                    "created_by": actor,
                    "metadata": {"record_id": str(record.id)},
                },
            )
            notifications.append(notification)
            if created:
                _schedule_notification(notification)
    return notifications


@transaction.atomic
def queue_summary_parent_notifications(
    *, enrollment, date_from, date_to, scope=None, channels=None, actor=None
):
    metrics = enrollment_metrics(
        enrollment=enrollment,
        date_from=date_from,
        date_to=date_to,
        scope=scope,
        include_excused=True,
    )
    policy = AttendancePolicy.objects.filter(
        school=enrollment.school,
        academic_year=enrollment.academic_year,
        is_active=True,
    ).first()
    requested_channels = channels or (policy.notification_channels if policy else [])
    student = enrollment.student
    subject = f"خلاصه حضور و غیاب {student.full_name}"
    message = (
        f"بازه {date_from} تا {date_to}: کل جلسات {metrics['total_sessions']}، "
        f"غیبت {metrics['absence_count']} ({metrics['absence_percent']}٪)، "
        f"موجه {metrics['excused_absence_count']}، "
        f"غیرموجه {metrics['unexcused_absence_count']}، "
        f"تأخیر {metrics['late_count']} و خروج زودهنگام {metrics['early_leave_count']}."
    )
    notifications = []
    for guardian in _guardians_for_student(student):
        guardian_channels = requested_channels or _default_channels_for_guardian(guardian)
        for channel in guardian_channels:
            dedupe_key = _notification_dedupe_key(
                "summary",
                enrollment.id,
                date_from,
                date_to,
                scope or "all",
                guardian.id,
                channel,
            )
            notification, created = ParentNotification.objects.get_or_create(
                dedupe_key=dedupe_key,
                defaults={
                    "school": enrollment.school,
                    "student": student,
                    "enrollment": enrollment,
                    "guardian": guardian,
                    "kind": ParentNotification.Kind.SUMMARY,
                    "channel": channel,
                    "recipient": _notification_recipient(guardian, channel),
                    "subject": subject,
                    "message": message,
                    "created_by": actor,
                    "metadata": {
                        "enrollment_id": str(enrollment.id),
                        "date_from": str(date_from),
                        "date_to": str(date_to),
                        "scope": scope,
                        "metrics": {key: str(value) for key, value in metrics.items()},
                    },
                },
            )
            notifications.append(notification)
            if created:
                _schedule_notification(notification)
    return notifications


@transaction.atomic
def evaluate_policy_alerts(*, policy, actor=None, request=None):
    policy = (
        AttendancePolicy.objects.select_for_update(of=("self",))
        .select_related("school", "academic_year")
        .get(pk=policy.pk)
    )
    date_from, date_to = attendance_date_range(
        academic_year=policy.academic_year,
        lookback_days=policy.lookback_days,
    )
    enrollments = Enrollment.objects.filter(
        school=policy.school,
        academic_year=policy.academic_year,
        status=Enrollment.Status.ACTIVE,
    ).select_related("student", "school", "academic_year", "class_section")
    created_or_updated = []
    resolved = []
    enrollment_list = list(enrollments)
    enrollment_ids = [enrollment.id for enrollment in enrollment_list]
    metrics_by_scope = {
        scope: enrollment_metrics_map(
            enrollment_ids=enrollment_ids,
            date_from=date_from,
            date_to=date_to,
            scope=scope,
            include_excused=policy.include_excused_absences,
        )
        for scope in [AttendanceSession.Scope.DAILY, AttendanceSession.Scope.PERIOD]
    }
    for enrollment in enrollment_list:
        for scope in [AttendanceSession.Scope.DAILY, AttendanceSession.Scope.PERIOD]:
            metrics = metrics_by_scope[scope][enrollment.id]
            count = metrics["absence_count"]
            percent = metrics["absence_percent"]
            severity = None
            if metrics["total_sessions"]:
                if (
                    count >= policy.critical_absence_count
                    or percent >= policy.critical_absence_percent
                ):
                    severity = AttendanceAlert.Severity.CRITICAL
                elif (
                    count >= policy.warning_absence_count
                    or percent >= policy.warning_absence_percent
                ):
                    severity = AttendanceAlert.Severity.WARNING

            active_alerts = AttendanceAlert.objects.select_for_update().filter(
                policy=policy,
                enrollment=enrollment,
                scope=scope,
                status__in=[
                    AttendanceAlert.Status.OPEN,
                    AttendanceAlert.Status.ACKNOWLEDGED,
                ],
            )
            matching_alert = active_alerts.filter(severity=severity).first() if severity else None
            for stale_alert in active_alerts.exclude(pk=getattr(matching_alert, "pk", None)):
                stale_alert.status = AttendanceAlert.Status.RESOLVED
                stale_alert.resolved_by = actor
                stale_alert.resolved_at = timezone.now()
                stale_alert.save(
                    update_fields=["status", "resolved_by", "resolved_at", "updated_at"]
                )
                resolved.append(stale_alert)
            if not severity:
                continue

            if matching_alert:
                alert = matching_alert
                alert.period_start = date_from
                alert.period_end = date_to
                alert.absence_count = count
                alert.total_sessions = metrics["total_sessions"]
                alert.absence_percent = percent
                alert.save(
                    update_fields=[
                        "period_start",
                        "period_end",
                        "absence_count",
                        "total_sessions",
                        "absence_percent",
                        "updated_at",
                    ]
                )
            else:
                alert = AttendanceAlert.objects.create(
                    policy=policy,
                    school=policy.school,
                    academic_year=policy.academic_year,
                    enrollment=enrollment,
                    scope=scope,
                    severity=severity,
                    period_start=date_from,
                    period_end=date_to,
                    absence_count=count,
                    total_sessions=metrics["total_sessions"],
                    absence_percent=percent,
                )
            created_or_updated.append(alert)
            if policy.notify_guardians:
                _queue_alert_notifications(alert=alert, policy=policy, actor=actor)

    record_audit(
        action="attendance.alerts_evaluated",
        actor=actor,
        request=request,
        entity=policy,
        organization_id=policy.organization_id,
        school_id=policy.school_id,
        changes={
            "active_alert_ids": [str(item.id) for item in created_or_updated],
            "resolved_alert_ids": [str(item.id) for item in resolved],
            "date_from": str(date_from),
            "date_to": str(date_to),
        },
    )
    return created_or_updated


def _queue_alert_notifications(*, alert, policy, actor=None):
    student = alert.enrollment.student
    requested_channels = policy.notification_channels or []
    subject = f"هشدار غیبت {student.full_name}"
    message = (
        f"در بازه {alert.period_start} تا {alert.period_end}، "
        f"{alert.absence_count} غیبت از {alert.total_sessions} جلسه "
        f"({alert.absence_percent}٪) ثبت شده است. سطح هشدار: {alert.get_severity_display()}."
    )
    for guardian in _guardians_for_student(student):
        guardian_channels = requested_channels or _default_channels_for_guardian(guardian)
        for channel in guardian_channels:
            dedupe_key = _notification_dedupe_key(
                "alert",
                alert.id,
                alert.absence_count,
                alert.total_sessions,
                guardian.id,
                channel,
            )
            notification, created = ParentNotification.objects.get_or_create(
                dedupe_key=dedupe_key,
                defaults={
                    "school": alert.school,
                    "student": student,
                    "enrollment": alert.enrollment,
                    "guardian": guardian,
                    "alert": alert,
                    "kind": ParentNotification.Kind.ALERT,
                    "channel": channel,
                    "recipient": _notification_recipient(guardian, channel),
                    "subject": subject,
                    "message": message,
                    "created_by": actor,
                    "metadata": {"alert_id": str(alert.id)},
                },
            )
            if created:
                _schedule_notification(notification)


@transaction.atomic
def acknowledge_alert(*, alert, actor, request=None):
    alert = AttendanceAlert.all_objects.select_for_update().get(pk=alert.pk)
    if alert.status != AttendanceAlert.Status.OPEN:
        raise ValidationError("فقط هشدار باز قابل مشاهده‌گذاری است.")
    alert.status = AttendanceAlert.Status.ACKNOWLEDGED
    alert.acknowledged_by = actor
    alert.acknowledged_at = timezone.now()
    alert.save(update_fields=["status", "acknowledged_by", "acknowledged_at", "updated_at"])
    record_audit(
        action="attendance.alert_acknowledged",
        actor=actor,
        request=request,
        entity=alert,
        organization_id=alert.organization_id,
        school_id=alert.school_id,
    )
    return alert


@transaction.atomic
def resolve_alert(*, alert, actor, request=None):
    alert = AttendanceAlert.all_objects.select_for_update().get(pk=alert.pk)
    if alert.status == AttendanceAlert.Status.RESOLVED:
        return alert
    alert.status = AttendanceAlert.Status.RESOLVED
    alert.resolved_by = actor
    alert.resolved_at = timezone.now()
    alert.save(update_fields=["status", "resolved_by", "resolved_at", "updated_at"])
    record_audit(
        action="attendance.alert_resolved",
        actor=actor,
        request=request,
        entity=alert,
        organization_id=alert.organization_id,
        school_id=alert.school_id,
    )
    return alert
