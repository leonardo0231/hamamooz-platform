from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIRequestFactory

from hamamooz.apps.academics.models import Assessment, Score
from hamamooz.apps.academics.services import bulk_upsert_scores
from hamamooz.apps.accounts.models import Role, RoleAssignment
from hamamooz.apps.core.models import AuditEvent
from hamamooz.apps.core.services import get_client_ip
from hamamooz.apps.organizations.models import ClassSection
from hamamooz.apps.reports.models import ReportArchive
from hamamooz.apps.reports.services import (
    _local_media_file_url,
    build_report_snapshot,
    build_student_snapshot,
    render_report_pdf,
)
from hamamooz.apps.students.models import Enrollment, Student
from hamamooz.apps.students.services import transfer_enrollment


def locked_assessment_with_scores(base_data):
    assessment = Assessment.objects.create(
        course_offering=base_data["offering1"],
        assessment_type=base_data["final"],
        title="گزارش نهایی",
        assessment_date=date(2026, 12, 20),
        max_score=Decimal("20"),
        weight=Decimal("2"),
        created_by=base_data["teacher1"],
    )
    bulk_upsert_scores(
        assessment=assessment,
        entries=[
            {
                "enrollment": enrollment,
                "value": Decimal(value),
                "status": Score.Status.PRESENT,
            }
            for enrollment, value in zip(base_data["enrollments"], ["18", "16"], strict=True)
        ],
        actor=base_data["teacher1"],
    )
    assessment.status = Assessment.Status.LOCKED
    assessment.save(update_fields=["status"])
    return assessment


@pytest.mark.django_db
def test_group_snapshot_recalculates_class_only_once(base_data, monkeypatch):
    locked_assessment_with_scores(base_data)
    from hamamooz.apps.reports import services

    original = services.recalculate_class_term
    calls = []

    def counted_recalculation(class_section, term):
        calls.append((class_section.id, term.id))
        return original(class_section, term)

    monkeypatch.setattr(services, "recalculate_class_term", counted_recalculation)
    snapshot = build_report_snapshot(
        ReportArchive.ReportType.CLASS_REPORT_CARDS,
        base_data["term"],
        class_section=base_data["class1"],
    )

    assert len(calls) == 1
    assert len(snapshot["reports"]) == 2
    assert {item["summary"]["average"] for item in snapshot["reports"]} == {"18.00", "16.00"}


@pytest.mark.django_db
def test_historical_transferred_enrollment_report_does_not_crash(base_data):
    locked_assessment_with_scores(base_data)
    original = base_data["enrollments"][0]
    transfer_enrollment(
        enrollment=original,
        school=base_data["school2"],
        grade_level=base_data["grade"],
        class_section=base_data["class2"],
        student_number="historical-target",
        transfer_date=date(2027, 1, 1),
        reason="انتقال بعد از ارزیابی",
        actor=base_data["manager"],
    )
    original.refresh_from_db()

    snapshot = build_student_snapshot(original, base_data["term"])

    assert snapshot["summary"]["average"] == "18.00"
    assert snapshot["summary"]["class_rank"] is None


def test_local_media_urls_are_confined_to_media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    expected = (tmp_path / "logos" / "school.png").resolve().as_uri()

    assert _local_media_file_url("/media/logos/school.png") == expected
    assert _local_media_file_url("/media/../../etc/passwd") == ""
    assert _local_media_file_url("https://objects.example/logo.png") == (
        "https://objects.example/logo.png"
    )


@pytest.mark.django_db
def test_group_report_readiness_detects_changed_active_roster(api_client, base_data):
    locked_assessment_with_scores(base_data)
    departed = base_data["enrollments"][1]
    departed.status = Enrollment.Status.WITHDRAWN
    departed.left_on = date(2026, 12, 21)
    departed.save(update_fields=["status", "left_on"])
    student = Student.objects.create(
        organization=base_data["organization"],
        national_id="0012345684",
        first_name="بدون",
        last_name="نمره",
        birth_date=date(2012, 3, 3),
        gender=Student.Gender.FEMALE,
    )
    Enrollment.objects.create(
        student=student,
        school=base_data["school1"],
        academic_year=base_data["year"],
        grade_level=base_data["grade"],
        class_section=base_data["class1"],
        student_number="missing-score",
        enrolled_on=date(2026, 12, 21),
    )
    api_client.force_authenticate(base_data["manager"])

    response = api_client.post(
        "/api/v1/reports/",
        {
            "term": str(base_data["term"].id),
            "report_type": ReportArchive.ReportType.CLASS_REPORT_CARDS,
            "class_section": str(base_data["class1"].id),
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    individual_response = api_client.post(
        "/api/v1/reports/",
        {
            "term": str(base_data["term"].id),
            "report_type": ReportArchive.ReportType.STUDENT_REPORT_CARD,
            "enrollment": str(base_data["enrollments"][0].id),
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 400
    assert individual_response.status_code == 400


@pytest.mark.django_db
def test_dashboard_counts_missing_scores_against_exact_active_roster(api_client, base_data):
    assessment = Assessment.objects.create(
        course_offering=base_data["offering1"],
        assessment_type=base_data["continuous"],
        title="داشبورد",
        assessment_date=date(2026, 10, 1),
        created_by=base_data["teacher1"],
    )
    bulk_upsert_scores(
        assessment=assessment,
        entries=[
            {
                "enrollment": base_data["enrollments"][0],
                "value": Decimal("17"),
                "status": Score.Status.PRESENT,
            }
        ],
        actor=base_data["teacher1"],
    )
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        "/api/v1/dashboard/summary/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    assert response.data["counts"]["students"] == 2
    assert response.data["counts"]["missing_scores"] == 1


@pytest.mark.django_db
def test_mixed_roles_do_not_expand_teacher_only_report_or_audit_scope(api_client, base_data):
    RoleAssignment.objects.create(
        user=base_data["teacher2"],
        organization=base_data["organization"],
        school=base_data["school1"],
        role=Role.SCHOOL_MANAGER,
    )
    unrelated_class = ClassSection.objects.create(
        school=base_data["school2"],
        academic_year=base_data["year"],
        grade_level=base_data["grade"],
        code="7-unrelated",
        title="کلاس بدون تدریس",
        capacity=35,
    )
    unrelated_report = ReportArchive.objects.create(
        organization=base_data["organization"],
        school=base_data["school2"],
        academic_year=base_data["year"],
        term=base_data["term"],
        report_type=ReportArchive.ReportType.CLASS_REPORT_CARDS,
        class_section=unrelated_class,
        requested_by=base_data["teacher1"],
    )
    hidden_audit = AuditEvent.objects.create(
        actor=base_data["teacher1"],
        organization_id=base_data["organization"].id,
        school_id=base_data["school2"].id,
        action="other-user-action",
    )
    own_audit = AuditEvent.objects.create(
        actor=base_data["teacher2"],
        organization_id=base_data["organization"].id,
        school_id=base_data["school2"].id,
        action="own-action",
    )
    api_client.force_authenticate(base_data["teacher2"])

    report_response = api_client.get(
        f"/api/v1/reports/{unrelated_report.id}/",
        HTTP_X_SCHOOL_ID=str(base_data["school2"].id),
    )
    dashboard_response = api_client.get(
        "/api/v1/dashboard/summary/",
        HTTP_X_SCHOOL_ID=str(base_data["school2"].id),
    )

    assert report_response.status_code == 404
    activity_ids = {
        str(activity["id"]) for activity in dashboard_response.data["latest_activities"]
    }
    assert str(own_audit.id) in activity_ids
    assert str(hidden_audit.id) not in activity_ids


@pytest.mark.django_db
def test_health_endpoints_are_public_and_ready(api_client):
    live = api_client.get("/api/v1/health/live/")
    ready = api_client.get("/api/v1/health/ready/")
    assert live.status_code == 200
    assert ready.status_code == 200
    assert ready.data["database"] is True
    assert ready.data["cache"] is True


def test_forwarded_ip_is_trusted_only_when_explicitly_enabled(settings):
    request = APIRequestFactory().get(
        "/",
        HTTP_X_FORWARDED_FOR="203.0.113.10, 10.0.0.1",
        REMOTE_ADDR="127.0.0.1",
    )
    settings.TRUST_X_FORWARDED_FOR = False
    assert get_client_ip(request) == "127.0.0.1"
    settings.TRUST_X_FORWARDED_FOR = True
    assert get_client_ip(request) == "203.0.113.10"


@pytest.mark.django_db
def test_report_pdf_renders_with_security_update(base_data):
    locked_assessment_with_scores(base_data)
    snapshot = build_report_snapshot(
        ReportArchive.ReportType.STUDENT_REPORT_CARD,
        base_data["term"],
        enrollment=base_data["enrollments"][0],
    )
    pdf = render_report_pdf(snapshot)
    assert pdf.startswith(b"%PDF")
