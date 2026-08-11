from datetime import date
from decimal import Decimal

import pytest

from hamamooz.apps.academics.models import SubjectResult, TermResult
from hamamooz.apps.attendance.models import AttendanceRecord, AttendanceSession
from hamamooz.apps.attendance.services import bulk_record_attendance, finalize_attendance_session
from hamamooz.apps.evaluations.models import MetricScore, MonthlyEvaluation
from hamamooz.apps.reports.models import ReportArchive


@pytest.mark.django_db
def test_student_360_summary_returns_scoped_identity_and_current_enrollment(api_client, base_data):
    """A future regression that removes the scoped 360 composition must fail here."""
    student = base_data["students"][0]
    enrollment = base_data["enrollments"][0]
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        f"/api/v1/students/{student.id}/360/summary/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    assert response.data["student"] == {
        "id": str(student.id),
        "full_name": student.full_name,
        "status": "active",
    }
    assert response.data["current_enrollment"] == {
        "id": str(enrollment.id),
        "student_number": enrollment.student_number,
        "school": base_data["school1"].name,
        "academic_year": base_data["year"].title,
        "grade": base_data["grade"].title,
        "class_section": base_data["class1"].title,
        "status": "active",
    }
    assert "counseling" not in response.data


@pytest.mark.django_db
def test_student_360_academics_returns_visible_term_and_subject_results(api_client, base_data):
    """A removed scope filter or result composition must not expose an empty academic tab."""
    student = base_data["students"][0]
    enrollment = base_data["enrollments"][0]
    TermResult.objects.create(
        enrollment=enrollment,
        term=base_data["term"],
        average=Decimal("16.50"),
        class_rank=1,
        passed=True,
        formula_version="mvp-v1",
    )
    SubjectResult.objects.create(
        enrollment=enrollment,
        course_offering=base_data["offering1"],
        average=Decimal("17.25"),
        passed=True,
        formula_version="mvp-v1",
    )
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        f"/api/v1/students/{student.id}/360/academics/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    assert response.data["term_results"] == [
        {
            "enrollment": str(enrollment.id),
            "term": {"id": str(base_data["term"].id), "title": base_data["term"].title},
            "average": 16.5,
            "class_rank": 1,
            "passed": True,
            "formula_version": "mvp-v1",
        }
    ]
    assert response.data["subject_results"] == [
        {
            "enrollment": str(enrollment.id),
            "subject": base_data["subject"].title,
            "average": 17.25,
            "passed": True,
            "formula_version": "mvp-v1",
        }
    ]


@pytest.mark.django_db
def test_student_360_attendance_returns_finalized_year_metrics(api_client, base_data):
    """A 360 attendance tab must summarize finalized records rather than draft observations."""
    enrollment = base_data["enrollments"][0]
    session = AttendanceSession.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        class_section=base_data["class1"],
        session_date=date(2026, 10, 1),
        scope=AttendanceSession.Scope.DAILY,
        starts_at="08:00",
        ends_at="13:00",
        taken_by=base_data["manager"],
    )
    bulk_record_attendance(
        session=session,
        items=[
            {
                "enrollment": enrollment,
                "status": AttendanceRecord.Status.ABSENT_UNEXCUSED,
            },
            {
                "enrollment": base_data["enrollments"][1],
                "status": AttendanceRecord.Status.PRESENT,
            },
        ],
        actor=base_data["manager"],
    )
    finalize_attendance_session(session=session, actor=base_data["manager"])
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        f"/api/v1/students/{enrollment.student_id}/360/attendance/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    assert response.data == {
        "enrollment": str(enrollment.id),
        "date_from": "2026-09-23",
        "date_to": "2027-06-22",
        "metrics": {
            "total_sessions": 1,
            "absence_count": 1,
            "excused_absence_count": 0,
            "unexcused_absence_count": 1,
            "late_count": 0,
            "early_leave_count": 0,
            "absence_percent": 100.0,
        },
    }


@pytest.mark.django_db
def test_student_360_evaluations_returns_scoped_indicator_entries(api_client, base_data):
    """A 360 indicator tab must return the student's persisted, versioned measurements."""
    enrollment = base_data["enrollments"][0]
    evaluation = MonthlyEvaluation.objects.create(
        enrollment=enrollment,
        month_no=4,
        recorded_by=base_data["manager"],
        note="monthly observation",
    )
    MetricScore.objects.create(evaluation=evaluation, metric_code="EDU_01", value=4)
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        f"/api/v1/students/{enrollment.student_id}/360/evaluations/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    assert response.data["framework_version"] == "1.0"
    assert response.data["evaluations"][0]["month_no"] == 4
    assert response.data["evaluations"][0]["metric_scores"] == [
        {
            "metric_code": "EDU_01",
            "title": "\u0646\u0645\u0631\u0627\u062a \u062f\u0631\u0633\u06cc",
            "domain_code": "EDU",
            "domain_title": "\u0622\u0645\u0648\u0632\u0634\u06cc",
            "value": 4,
        }
    ]


@pytest.mark.django_db
def test_student_360_reports_returns_only_student_archives(api_client, base_data):
    """A 360 reports tab must not turn a class-wide archive into a student archive."""
    enrollment = base_data["enrollments"][0]
    report = ReportArchive.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        term=base_data["term"],
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        status=ReportArchive.Status.COMPLETED,
        enrollment=enrollment,
        requested_by=base_data["manager"],
        formula_version="mvp-v1",
        snapshot={"version": "mvp-v1"},
    )
    ReportArchive.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        term=base_data["term"],
        report_type=ReportArchive.ReportType.CLASS_REPORT_CARDS,
        class_section=base_data["class1"],
        requested_by=base_data["manager"],
    )
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        f"/api/v1/students/{enrollment.student_id}/360/reports/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.data["reports"]] == [str(report.id)]
    assert response.data["reports"][0]["report_type"] == "student_report_card"
    assert response.json()["reports"][0]["enrollment"] == str(enrollment.id)


@pytest.mark.django_db
def test_student_360_does_not_disclose_a_student_to_another_school(api_client, base_data):
    """A new 360 action must retain the parent ViewSet's tenant and school scope."""
    student = base_data["students"][0]
    api_client.force_authenticate(base_data["teacher2"])

    response = api_client.get(
        f"/api/v1/students/{student.id}/360/summary/",
        HTTP_X_SCHOOL_ID=str(base_data["school2"].id),
    )

    assert response.status_code == 404
