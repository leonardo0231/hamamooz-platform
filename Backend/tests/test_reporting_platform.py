from zipfile import ZipFile

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from hamamooz.apps.recommendations.models import Recommendation
from hamamooz.apps.reports.models import ReportArchive, ReportDraft, ReportTemplate
from hamamooz.apps.reports.services import (
    build_draft_snapshot,
    render_report_draft,
    render_report_html,
    render_report_pdf,
)


@pytest.mark.django_db
def test_report_draft_catalog_is_available_for_authorized_school_scope(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])
    response = api_client.get(
        "/api/v1/reports/drafts/", HTTP_X_SCHOOL_ID=str(base_data["school1"].id)
    )
    assert response.status_code == 200
    assert response.data["count"] == 0


@pytest.mark.django_db
def test_report_draft_snapshot_is_immutable_when_current_student_data_changes(base_data):
    template = ReportTemplate.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        code="student-safe",
        title="Student safe",
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        blocks=["student_identity", "academic_summary", "recommendations"],
    )
    draft = ReportDraft.objects.create(
        template=template,
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        term=base_data["term"],
        enrollment=base_data["enrollments"][0],
        snapshot={"reports": [{"student": {"full_name": "Original student"}}]},
        status=ReportDraft.Status.APPROVED,
        created_by=base_data["manager"],
        reviewed_by=base_data["manager"],
        reviewed_at=timezone.now(),
    )
    student = base_data["students"][0]
    student.first_name = "Changed"
    student.save(update_fields=["first_name", "updated_at"])

    draft.refresh_from_db()
    assert draft.snapshot["reports"][0]["student"]["full_name"] == "Original student"
    assert "counseling" not in draft.snapshot


@pytest.mark.django_db
def test_report_template_rejects_executable_or_unknown_blocks(base_data):
    template = ReportTemplate(
        organization=base_data["organization"],
        school=base_data["school1"],
        code="unsafe",
        title="Unsafe",
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        blocks=["{{ arbitrary_jinja }}"],
    )
    with pytest.raises(ValidationError):
        template.full_clean()


@pytest.mark.django_db
def test_report_template_allows_only_safe_a3_landscape_page_configuration(base_data):
    template = ReportTemplate(
        organization=base_data["organization"],
        school=base_data["school1"],
        code="class-a3",
        title="Class dashboard A3",
        report_type=ReportArchive.ReportType.CLASS_REPORT_CARDS,
        blocks=["student_identity", "academic_summary"],
        presentation={"page_size": "a3_landscape"},
    )
    template.full_clean()

    snapshot = build_draft_snapshot(
        template, term=base_data["term"], class_section=base_data["class1"]
    )
    assert "size: A3 landscape;" in render_report_html(snapshot)
    assert render_report_pdf(snapshot).startswith(b"%PDF")

    template.presentation = {"page_size": "A3 landscape; @import url(https://invalid.example)"}
    with pytest.raises(ValidationError):
        template.full_clean()


@pytest.mark.django_db
def test_report_snapshot_never_includes_counselor_audience_recommendations(base_data):
    enrollment = base_data["enrollments"][0]
    for audience, code in [
        (Recommendation.Audience.COUNSELOR, "private-counselor"),
        (Recommendation.Audience.PARENT, "released-parent"),
    ]:
        Recommendation.objects.create(
            organization=base_data["organization"],
            school=base_data["school1"],
            enrollment=enrollment,
            audience=audience,
            rule_code=code,
            rule_version=1,
            priority=Recommendation.Priority.MEDIUM,
            reason_snapshot={"test": True},
            generated_text="Generated recommendation.",
            approved_text="Approved recommendation.",
            status=Recommendation.Status.APPROVED,
            approved_at=timezone.now(),
        )
    template = ReportTemplate.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        code="recommendation-boundary",
        title="Recommendation boundary",
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        blocks=["student_identity", "recommendations"],
    )

    snapshot = build_draft_snapshot(template, term=base_data["term"], enrollment=enrollment)

    recommendations = snapshot["reports"][0]["product_context"]["approved_recommendations"]
    assert [item["audience"] for item in recommendations] == [Recommendation.Audience.PARENT]


@pytest.mark.django_db
def test_approved_docx_draft_renders_a_frozen_word_archive(base_data, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    template = ReportTemplate.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        code="student-word",
        title="Student Word report",
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        output_format=ReportTemplate.OutputFormat.DOCX,
        blocks=["student_identity", "academic_summary", "attendance_summary", "recommendations"],
    )
    snapshot = build_draft_snapshot(
        template, term=base_data["term"], enrollment=base_data["enrollments"][0]
    )
    draft = ReportDraft.objects.create(
        template=template,
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        term=base_data["term"],
        enrollment=base_data["enrollments"][0],
        snapshot=snapshot,
        status=ReportDraft.Status.APPROVED,
        created_by=base_data["manager"],
        reviewed_by=base_data["manager"],
        reviewed_at=timezone.now(),
    )

    rendered = render_report_draft(draft.id)
    archive = rendered.archive
    assert archive.output_format == ReportArchive.OutputFormat.DOCX
    assert archive.status == ReportArchive.Status.COMPLETED
    assert archive.output_file.name.endswith(".docx")
    with archive.output_file.open("rb") as stream, ZipFile(stream) as document:
        assert "word/document.xml" in document.namelist()
