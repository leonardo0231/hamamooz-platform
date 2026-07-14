from datetime import date
from decimal import Decimal

import pytest

from hamamooz.apps.academics.models import Assessment, Score
from hamamooz.apps.academics.services import bulk_upsert_scores
from hamamooz.apps.reports.models import ReportArchive
from hamamooz.apps.reports.services import generate_report
from hamamooz.apps.students.models import Enrollment, EnrollmentEvent
from hamamooz.apps.students.services import transfer_enrollment


@pytest.mark.django_db
def test_student_report_is_archived_as_pdf(base_data, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    assessment = Assessment.objects.create(
        course_offering=base_data["offering1"],
        assessment_type=base_data["final"],
        title="پایانی",
        assessment_date=date(2026, 12, 20),
        max_score=Decimal("20"),
        weight=Decimal("2"),
        created_by=base_data["teacher1"],
    )
    bulk_upsert_scores(
        assessment=assessment,
        entries=[
            {"enrollment": enrollment, "value": Decimal("18"), "status": Score.Status.PRESENT}
            for enrollment in base_data["enrollments"]
        ],
        actor=base_data["teacher1"],
    )
    assessment.status = Assessment.Status.LOCKED
    assessment.save(update_fields=["status"])
    report = ReportArchive.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        term=base_data["term"],
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        enrollment=base_data["enrollments"][0],
        requested_by=base_data["manager"],
    )
    generate_report(report.id)
    report.refresh_from_db()
    assert report.status == ReportArchive.Status.COMPLETED
    with report.output_file.open("rb") as output:
        assert output.read(4) == b"%PDF"
    assert report.snapshot["reports"][0]["student"]["national_id"] == "0012345678"


@pytest.mark.django_db
def test_official_report_api_requires_all_assessments_to_be_locked(api_client, base_data):
    assessment = Assessment.objects.create(
        course_offering=base_data["offering1"],
        assessment_type=base_data["final"],
        title="پایانی",
        assessment_date=date(2026, 12, 20),
        created_by=base_data["teacher1"],
    )
    api_client.force_authenticate(base_data["manager"])
    payload = {
        "term": str(base_data["term"].id),
        "report_type": ReportArchive.ReportType.STUDENT_REPORT_CARD,
        "enrollment": str(base_data["enrollments"][0].id),
    }
    response = api_client.post(
        "/api/v1/reports/",
        payload,
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert response.status_code == 400

    assessment.status = Assessment.Status.LOCKED
    assessment.save(update_fields=["status"])
    response = api_client.post(
        "/api/v1/reports/",
        payload,
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_transfer_preserves_source_and_creates_target_history(base_data):
    target = transfer_enrollment(
        enrollment=base_data["enrollments"][0],
        school=base_data["school2"],
        grade_level=base_data["grade"],
        class_section=base_data["class2"],
        student_number="2001",
        transfer_date=date(2026, 11, 1),
        reason="جابجایی محل سکونت",
        actor=base_data["manager"],
    )
    source = Enrollment.objects.get(id=base_data["enrollments"][0].id)
    assert source.status == Enrollment.Status.TRANSFERRED
    assert target.status == Enrollment.Status.ACTIVE
    assert source.events.filter(event_type=EnrollmentEvent.EventType.TRANSFER_OUT).exists()
    assert target.events.filter(event_type=EnrollmentEvent.EventType.TRANSFER_IN).exists()
