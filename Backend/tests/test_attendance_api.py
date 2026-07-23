from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from hamamooz.apps.attendance.models import (
    AttendanceAlert,
    AttendancePolicy,
    AttendanceRecord,
    AttendanceSession,
    ParentNotification,
)
from hamamooz.apps.attendance.serializers import (
    AttendanceBulkItemSerializer,
    CorrectAttendanceRecordSerializer,
)
from hamamooz.apps.attendance.services import (
    acknowledge_alert,
    bulk_record_attendance,
    evaluate_policy_alerts,
    finalize_attendance_session,
    queue_record_parent_notifications,
    review_absence_excuse,
    submit_absence_excuse,
)
from hamamooz.apps.students.models import Guardian, StudentGuardian


def attendance_headers(school):
    return {
        "HTTP_X_SCHOOL_ID": str(school.id),
        "HTTP_X_ORGANIZATION_ID": str(school.organization_id),
    }


def create_daily_session(base_data, *, session_date=date(2026, 10, 1)):
    return AttendanceSession.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        class_section=base_data["class1"],
        session_date=session_date,
        scope=AttendanceSession.Scope.DAILY,
        starts_at="08:00",
        ends_at="13:00",
        taken_by=base_data["manager"],
    )


@pytest.mark.django_db
def test_daily_attendance_bulk_mark_and_finalize(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])
    headers = attendance_headers(base_data["school1"])

    response = api_client.post(
        "/api/v1/attendance-sessions/",
        {
            "school": str(base_data["school1"].id),
            "academic_year": str(base_data["year"].id),
            "class_section": str(base_data["class1"].id),
            "session_date": "2026-10-01",
            "scope": "daily",
            "starts_at": "08:00:00",
            "ends_at": "13:00:00",
        },
        format="json",
        **headers,
    )
    assert response.status_code == 201, response.data
    session_id = response.data["id"]

    response = api_client.post(
        f"/api/v1/attendance-sessions/{session_id}/bulk-mark/",
        {
            "records": [
                {
                    "enrollment": str(base_data["enrollments"][0].id),
                    "status": "present",
                    "arrival_time": "08:12:00",
                    "departure_time": "12:45:00",
                },
                {
                    "enrollment": str(base_data["enrollments"][1].id),
                    "status": "absent_unexcused",
                },
            ]
        },
        format="json",
        **headers,
    )
    assert response.status_code == 200, response.data
    present = next(item for item in response.data if item["status"] == "present")
    assert present["late_minutes"] == 12
    assert present["early_leave_minutes"] == 15

    response = api_client.post(
        f"/api/v1/attendance-sessions/{session_id}/finalize/",
        {},
        format="json",
        **headers,
    )
    assert response.status_code == 200, response.data
    assert response.data["status"] == AttendanceSession.Status.FINALIZED


@pytest.mark.django_db
def test_teacher_can_record_own_period_attendance(api_client, base_data):
    api_client.force_authenticate(base_data["teacher1"])
    headers = attendance_headers(base_data["school1"])
    response = api_client.post(
        "/api/v1/attendance-sessions/",
        {
            "school": str(base_data["school1"].id),
            "academic_year": str(base_data["year"].id),
            "class_section": str(base_data["class1"].id),
            "term": str(base_data["term"].id),
            "course_offering": str(base_data["offering1"].id),
            "session_date": "2026-10-02",
            "scope": "period",
            "period_number": 2,
            "starts_at": "09:00:00",
            "ends_at": "10:00:00",
        },
        format="json",
        **headers,
    )
    assert response.status_code == 201, response.data
    assert response.data["scope"] == AttendanceSession.Scope.PERIOD


@pytest.mark.django_db
def test_finalize_rejects_incomplete_roster(base_data):
    session = create_daily_session(base_data)
    bulk_record_attendance(
        session=session,
        items=[{"enrollment": base_data["enrollments"][0], "status": "present"}],
        actor=base_data["manager"],
    )
    with pytest.raises(Exception) as exc:
        finalize_attendance_session(session=session, actor=base_data["manager"])
    assert "missing_enrollment_ids" in str(exc.value)


@pytest.mark.django_db
def test_excused_absence_requires_review(base_data):
    assert not AttendanceBulkItemSerializer(
        data={
            "enrollment": base_data["enrollments"][0].id,
            "status": AttendanceRecord.Status.ABSENT_EXCUSED,
        }
    ).is_valid()
    assert not CorrectAttendanceRecordSerializer(
        data={"status": AttendanceRecord.Status.ABSENT_EXCUSED, "reason": "اصلاح تست"}
    ).is_valid()

    session = create_daily_session(base_data)
    record = AttendanceRecord(
        session=session,
        enrollment=base_data["enrollments"][0],
        status=AttendanceRecord.Status.ABSENT_EXCUSED,
        recorded_by=base_data["manager"],
    )
    with pytest.raises(DjangoValidationError):
        record.full_clean(exclude=["id"])


@pytest.mark.django_db
def test_excuse_evidence_and_approval_workflow(base_data):
    session = create_daily_session(base_data)
    record = bulk_record_attendance(
        session=session,
        items=[
            {
                "enrollment": base_data["enrollments"][0],
                "status": AttendanceRecord.Status.ABSENT_UNEXCUSED,
            }
        ],
        actor=base_data["manager"],
    )[0]
    evidence = SimpleUploadedFile(
        "medical.pdf",
        b"%PDF-1.7\nminimal test document",
        content_type="application/pdf",
    )
    submitted = submit_absence_excuse(
        record=record,
        reason="گواهی پزشک",
        evidence_files=[evidence],
        actor=base_data["manager"],
    )
    assert submitted.excuse_status == AttendanceRecord.ExcuseStatus.PENDING
    assert submitted.evidence_files.count() == 1

    approved = review_absence_excuse(
        record=submitted,
        approved=True,
        note="مدرک بررسی شد",
        actor=base_data["deputy"],
    )
    assert approved.status == AttendanceRecord.Status.ABSENT_EXCUSED
    assert approved.excuse_status == AttendanceRecord.ExcuseStatus.APPROVED
    assert approved.reviewed_by == base_data["deputy"]
    assert approved.history.count() == 2


@pytest.mark.django_db
def test_student_report_calculates_count_and_percent(api_client, base_data):
    for offset, statuses in enumerate(
        [
            [AttendanceRecord.Status.ABSENT_UNEXCUSED, AttendanceRecord.Status.PRESENT],
            [AttendanceRecord.Status.PRESENT, AttendanceRecord.Status.PRESENT],
        ]
    ):
        session = create_daily_session(
            base_data, session_date=date(2026, 10, 1) + timedelta(days=offset)
        )
        bulk_record_attendance(
            session=session,
            items=[
                {"enrollment": enrollment, "status": record_status}
                for enrollment, record_status in zip(
                    base_data["enrollments"], statuses, strict=True
                )
            ],
            actor=base_data["manager"],
        )
        finalize_attendance_session(session=session, actor=base_data["manager"])

    api_client.force_authenticate(base_data["manager"])
    response = api_client.get(
        "/api/v1/attendance-reports/student/",
        {
            "enrollment": str(base_data["enrollments"][0].id),
            "date_from": "2026-10-01",
            "date_to": "2026-10-02",
            "scope": AttendanceSession.Scope.DAILY,
        },
        **attendance_headers(base_data["school1"]),
    )
    assert response.status_code == 200, response.data
    assert response.data["metrics"]["total_sessions"] == 2
    assert response.data["metrics"]["absence_count"] == 1
    assert Decimal(response.data["metrics"]["absence_percent"]) == Decimal("50.00")


@pytest.mark.django_db
def test_cross_school_report_is_denied(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])
    response = api_client.get(
        "/api/v1/attendance-reports/student/",
        {"enrollment": str(base_data["enrollments"][0].id)},
        **attendance_headers(base_data["school2"]),
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_alert_evaluation_is_idempotent_after_acknowledge(base_data, monkeypatch):
    monkeypatch.setattr(
        "hamamooz.apps.attendance.selectors.timezone.localdate",
        lambda: date(2026, 10, 31),
    )
    for offset, statuses in enumerate(
        [
            [AttendanceRecord.Status.ABSENT_UNEXCUSED, AttendanceRecord.Status.PRESENT],
            [AttendanceRecord.Status.PRESENT, AttendanceRecord.Status.PRESENT],
        ]
    ):
        session = create_daily_session(
            base_data, session_date=date(2026, 10, 1) + timedelta(days=offset)
        )
        bulk_record_attendance(
            session=session,
            items=[
                {"enrollment": enrollment, "status": record_status}
                for enrollment, record_status in zip(
                    base_data["enrollments"], statuses, strict=True
                )
            ],
            actor=base_data["manager"],
        )
        finalize_attendance_session(session=session, actor=base_data["manager"])

    policy = AttendancePolicy.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        warning_absence_count=1,
        critical_absence_count=2,
        warning_absence_percent=Decimal("90"),
        critical_absence_percent=Decimal("100"),
        lookback_days=365,
        notify_guardians=False,
    )
    alerts = evaluate_policy_alerts(policy=policy, actor=base_data["manager"])
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.severity == AttendanceAlert.Severity.WARNING
    acknowledge_alert(alert=alert, actor=base_data["manager"])

    repeated = evaluate_policy_alerts(policy=policy, actor=base_data["manager"])
    assert len(repeated) == 1
    assert repeated[0].id == alert.id
    assert repeated[0].status == AttendanceAlert.Status.ACKNOWLEDGED


@pytest.mark.django_db
def test_parent_notification_is_bound_to_enrollment(base_data, settings):
    settings.ATTENDANCE_ASYNC_NOTIFICATIONS = False
    guardian = Guardian.objects.create(
        organization=base_data["organization"],
        first_name="ولی",
        last_name="دانش‌آموز",
        phone_primary="09120000000",
        email="guardian@example.com",
    )
    StudentGuardian.objects.create(
        student=base_data["students"][0],
        guardian=guardian,
        relationship=StudentGuardian.Relationship.FATHER,
        is_primary=True,
    )
    session = create_daily_session(base_data)
    record = bulk_record_attendance(
        session=session,
        items=[
            {
                "enrollment": base_data["enrollments"][0],
                "status": AttendanceRecord.Status.ABSENT_UNEXCUSED,
            }
        ],
        actor=base_data["manager"],
    )[0]
    notifications = queue_record_parent_notifications(
        record=record,
        channels=[ParentNotification.Channel.IN_APP],
        actor=base_data["manager"],
    )
    assert len(notifications) == 1
    notification = notifications[0]
    notification.refresh_from_db()
    assert notification.enrollment_id == base_data["enrollments"][0].id
    assert notification.status == ParentNotification.Status.SENT


@pytest.mark.django_db
def test_invalid_evidence_signature_is_rejected(base_data):
    session = create_daily_session(base_data)
    record = bulk_record_attendance(
        session=session,
        items=[
            {
                "enrollment": base_data["enrollments"][0],
                "status": AttendanceRecord.Status.ABSENT_UNEXCUSED,
            }
        ],
        actor=base_data["manager"],
    )[0]
    fake_pdf = SimpleUploadedFile("fake.pdf", b"not a pdf", content_type="application/pdf")
    with pytest.raises(DjangoValidationError):
        submit_absence_excuse(
            record=record,
            reason="مدرک نامعتبر",
            evidence_files=[fake_pdf],
            actor=base_data["manager"],
        )
