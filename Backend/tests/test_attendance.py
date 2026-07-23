from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError

from hamamooz.apps.attendance.models import (
    AttendancePolicy,
    AttendanceRecord,
    AttendanceSession,
    ParentNotification,
)
from hamamooz.apps.attendance.notifications import dispatch_notification
from hamamooz.apps.attendance.selectors import active_enrollments_for_class
from hamamooz.apps.attendance.serializers import SubmitAbsenceExcuseSerializer
from hamamooz.apps.attendance.services import (
    bulk_record_attendance,
    cancel_attendance_session,
    correct_attendance_record,
    evaluate_policy_alerts,
    finalize_attendance_session,
    review_absence_excuse,
    submit_absence_excuse,
)
from hamamooz.apps.organizations.models import ClassSection
from hamamooz.apps.students.models import Guardian, StudentGuardian
from hamamooz.apps.students.services import change_class


def make_daily_session(base_data, *, day=date(2026, 10, 1)):
    return AttendanceSession.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        class_section=base_data["class1"],
        term=base_data["term"],
        session_date=day,
        scope=AttendanceSession.Scope.DAILY,
        taken_by=base_data["manager"],
    )


@pytest.mark.django_db
def test_bulk_finalize_and_correct_attendance(base_data):
    session = make_daily_session(base_data)
    records = bulk_record_attendance(
        session=session,
        actor=base_data["manager"],
        items=[
            {"enrollment": base_data["enrollments"][0], "status": AttendanceRecord.Status.PRESENT},
            {
                "enrollment": base_data["enrollments"][1],
                "status": AttendanceRecord.Status.ABSENT_UNEXCUSED,
            },
        ],
    )
    assert len(records) == 2
    finalized = finalize_attendance_session(session=session, actor=base_data["manager"])
    assert finalized.status == AttendanceSession.Status.FINALIZED

    absent = AttendanceRecord.objects.get(session=session, enrollment=base_data["enrollments"][1])
    corrected = correct_attendance_record(
        record=absent,
        data={"status": AttendanceRecord.Status.PRESENT, "note": "اصلاح رسمی"},
        reason="ثبت اشتباه اولیه",
        actor=base_data["manager"],
    )
    assert corrected.status == AttendanceRecord.Status.PRESENT
    assert corrected.revision == 1
    assert corrected.history.count() == 1


@pytest.mark.django_db
def test_finalize_rejects_incomplete_roster(base_data):
    session = make_daily_session(base_data)
    bulk_record_attendance(
        session=session,
        actor=base_data["manager"],
        items=[
            {"enrollment": base_data["enrollments"][0], "status": AttendanceRecord.Status.PRESENT}
        ],
    )
    with pytest.raises(ValidationError):
        finalize_attendance_session(session=session, actor=base_data["manager"])


@pytest.mark.django_db
def test_excuse_review_records_revision(base_data):
    session = make_daily_session(base_data)
    records = bulk_record_attendance(
        session=session,
        actor=base_data["manager"],
        items=[
            {
                "enrollment": enrollment,
                "status": AttendanceRecord.Status.ABSENT_UNEXCUSED,
            }
            for enrollment in base_data["enrollments"]
        ],
    )
    finalize_attendance_session(session=session, actor=base_data["manager"])
    record = submit_absence_excuse(
        record=records[0],
        reason="بیماری",
        evidence_files=[],
        actor=base_data["manager"],
    )
    assert record.excuse_status == AttendanceRecord.ExcuseStatus.PENDING
    record = review_absence_excuse(
        record=record,
        approved=True,
        note="تأیید شد",
        actor=base_data["deputy"],
    )
    assert record.status == AttendanceRecord.Status.ABSENT_EXCUSED
    assert record.excuse_status == AttendanceRecord.ExcuseStatus.APPROVED
    assert record.history.count() == 2


@pytest.mark.django_db
def test_roster_is_effective_dated_after_class_change(base_data):
    new_class = ClassSection.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        grade_level=base_data["grade"],
        code="7-history",
        title="هفتم تاریخچه",
        capacity=35,
    )
    source = base_data["enrollments"][0]
    target = change_class(
        enrollment=source,
        new_class=new_class,
        reason="تغییر برنامه",
        effective_date=date(2026, 10, 15),
        actor=base_data["manager"],
    )
    before = make_daily_session(base_data, day=date(2026, 10, 10))
    after = AttendanceSession.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        class_section=new_class,
        term=base_data["term"],
        session_date=date(2026, 10, 20),
        scope=AttendanceSession.Scope.DAILY,
        taken_by=base_data["manager"],
    )
    assert source.id in set(active_enrollments_for_class(before).values_list("id", flat=True))
    assert target.id in set(active_enrollments_for_class(after).values_list("id", flat=True))


@pytest.mark.django_db
def test_cancelled_session_records_are_not_exposed(api_client, base_data):
    session = make_daily_session(base_data)
    bulk_record_attendance(
        session=session,
        actor=base_data["manager"],
        items=[
            {"enrollment": base_data["enrollments"][0], "status": AttendanceRecord.Status.PRESENT}
        ],
    )
    cancel_attendance_session(
        session=session,
        actor=base_data["manager"],
        reason="تعطیلی مدرسه",
    )
    api_client.force_authenticate(base_data["manager"])
    response = api_client.get(
        "/api/v1/attendance-records/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert response.status_code == 200
    assert response.data["results"] == []


@pytest.mark.django_db
def test_alert_evaluation_is_idempotent(base_data, monkeypatch):
    monkeypatch.setattr(
        "hamamooz.apps.attendance.selectors.timezone.localdate",
        lambda: date(2026, 10, 2),
    )
    policy = AttendancePolicy.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        warning_absence_count=1,
        critical_absence_count=2,
        warning_absence_percent=1,
        critical_absence_percent=90,
        lookback_days=365,
        notify_guardians=False,
    )
    session = make_daily_session(base_data)
    bulk_record_attendance(
        session=session,
        actor=base_data["manager"],
        items=[
            {
                "enrollment": enrollment,
                "status": AttendanceRecord.Status.ABSENT_UNEXCUSED,
            }
            for enrollment in base_data["enrollments"]
        ],
    )
    finalize_attendance_session(session=session, actor=base_data["manager"])
    first = evaluate_policy_alerts(policy=policy, actor=base_data["manager"])
    second = evaluate_policy_alerts(policy=policy, actor=base_data["manager"])
    assert len(first) == 2
    assert {item.id for item in first} == {item.id for item in second}


@pytest.mark.django_db
def test_in_app_notification_is_not_falsely_marked_sent(base_data):
    guardian = Guardian.objects.create(
        organization=base_data["organization"],
        first_name="ولی",
        last_name="آزمون",
        phone_primary="09120000000",
    )
    StudentGuardian.objects.create(
        student=base_data["students"][0],
        guardian=guardian,
        relationship=StudentGuardian.Relationship.FATHER,
        is_primary=True,
    )
    notification = ParentNotification.objects.create(
        school=base_data["school1"],
        student=base_data["students"][0],
        enrollment=base_data["enrollments"][0],
        guardian=guardian,
        kind=ParentNotification.Kind.SUMMARY,
        channel=ParentNotification.Channel.IN_APP,
        subject="آزمون",
        message="پیام",
        dedupe_key="test-in-app-skip",
        created_by=base_data["manager"],
    )
    dispatch_notification(notification)
    notification.refresh_from_db()
    assert notification.status == ParentNotification.Status.SKIPPED
    assert notification.sent_at is None


def test_excuse_evidence_total_size_is_limited(settings):
    settings.ATTENDANCE_MAX_EVIDENCE_TOTAL_SIZE = 10
    serializer = SubmitAbsenceExcuseSerializer(
        data={
            "reason": "مدرک آزمایشی",
            "evidence_files": [
                SimpleUploadedFile("a.pdf", b"%PDF-123"),
                SimpleUploadedFile("b.pdf", b"%PDF-456"),
            ],
        }
    )
    assert not serializer.is_valid()
    assert "evidence_files" in serializer.errors
