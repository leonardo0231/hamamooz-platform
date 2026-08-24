import re
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from hamamooz.apps.academics.models import Assessment, Score
from hamamooz.apps.academics.services import bulk_upsert_scores
from hamamooz.apps.accounts.models import Role, RoleAssignment
from hamamooz.apps.recommendations.models import Recommendation
from hamamooz.apps.reports.models import ReportArchive, ReportDraft, ReportTemplate
from hamamooz.apps.reports.serializers import ReportDraftContentSerializer


def test_report_card_layout_catalog_is_exact_and_declares_period_and_page_size():
    """Removing, renaming, or mis-sizing a required official layout must fail."""
    from hamamooz.apps.reports.services import REPORT_CARD_LAYOUTS

    assert tuple(REPORT_CARD_LAYOUTS) == (
        "analytical_term_1",
        "analytical_term_2",
        "analytical_annual",
        "final_term_1",
        "final_term_2",
        "final_annual",
        "summer_report",
    )
    assert {
        key: (value["period_type"], value["page_size"])
        for key, value in REPORT_CARD_LAYOUTS.items()
    } == {
        "analytical_term_1": ("term", "a3_landscape"),
        "analytical_term_2": ("term", "a3_landscape"),
        "analytical_annual": ("annual", "a3_landscape"),
        "final_term_1": ("term", "a4_portrait"),
        "final_term_2": ("term", "a4_portrait"),
        "final_annual": ("annual", "a4_portrait"),
        "summer_report": ("summer", "a4_portrait"),
    }


def _locked_term_scores(base_data):
    assessment = Assessment.objects.create(
        course_offering=base_data["offering1"],
        assessment_type=base_data["final"],
        title="نمره رسمی کارنامه",
        assessment_date=date(2026, 12, 20),
        max_score=Decimal("20"),
        weight=Decimal("1"),
        created_by=base_data["teacher1"],
    )
    bulk_upsert_scores(
        assessment=assessment,
        entries=[
            {"enrollment": enrollment, "value": Decimal(value), "status": Score.Status.PRESENT}
            for enrollment, value in zip(
                base_data["enrollments"], ("18", "16"), strict=True
            )
        ],
        actor=base_data["teacher1"],
    )
    assessment.status = Assessment.Status.LOCKED
    assessment.locked_at = timezone.now()
    assessment.save(update_fields=["status", "locked_at"])
    return assessment


def _minimal_snapshot(layout_key):
    return {
        "schema_version": "report-card-v2",
        "layout_key": layout_key,
        "period": {"type": "term", "label": "نوبت اول"},
        "reports": [
            {
                "organization": {"name": "هم‌آموز"},
                "school": {
                    "name": "مدرسه نمونه",
                    "branch": "",
                    "address": "تهران",
                    "phone": "۰۲۱",
                    "manager": "مدیر مدرسه",
                    "logo_url": "",
                },
                "student": {
                    "full_name": "دانش‌آموز نمونه",
                    "national_id": "0012345678",
                    "student_number": "101",
                    "photo_url": "",
                },
                "academic": {
                    "year": "۱۴۰۵-۱۴۰۶",
                    "term": "نوبت اول",
                    "grade": "هفتم",
                    "class": "هفتم الف",
                },
                "subjects": [
                    {
                        "title": "ریاضی",
                        "coefficient": "2.00",
                        "continuous": "17.00",
                        "midterm": None,
                        "final": "18.00",
                        "first_term_score": "17.00",
                        "second_term_score": "18.00",
                        "average": "18.00",
                        "passed": True,
                    }
                ],
                "summary": {
                    "average": "18.00",
                    "class_rank": 1,
                    "grade_rank": 2,
                    "school_rank": 3,
                    "class_population": 20,
                    "grade_population": 60,
                    "school_population": 180,
                    "passed": True,
                    "status_label": "قبول",
                    "formula_version": "v1",
                },
                "rank_visibility": {"class": True, "grade": True, "school": False},
                "product_context": {
                    "attendance": {
                        "finalized_session_count": 10,
                        "unexcused_absence_count": 0,
                    },
                    "evaluations": [],
                    "activities": [],
                    "approved_recommendations": [
                        {"audience": "parent", "approved_text": "ادامه تلاش منظم"}
                    ],
                },
                "chart_svg": (
                    '<svg viewBox="0 0 300 80" role="img" '
                    'aria-label="نمودار نمرات"><rect width="270" height="14" /></svg>'
                ),
            }
        ],
        "template": {
            "blocks": [
                "student_identity",
                "academic_summary",
                "recommendations",
                "signatures",
            ],
            "presentation": {},
            "output_format": "pdf",
        },
        "content_overrides": {},
        "official": {
            "tracking_code": "RC-1405-000001",
            "version": 1,
            "approved_at": "2026-08-24T10:00:00+00:00",
            "approved_by": "مدیر مدرسه",
        },
    }


def test_source_fingerprint_is_canonical_and_changes_with_locked_academic_facts():
    """Key order/approval metadata must not stale a draft, but a score change must."""
    from hamamooz.apps.reports.services import source_fingerprint

    first = _minimal_snapshot("final_term_1")
    second = dict(reversed(list(deepcopy(first).items())))
    second["official"] = {"tracking_code": "different", "version": 99}

    assert source_fingerprint(first) == source_fingerprint(second)
    second["reports"][0]["subjects"][0]["average"] = "17.50"
    assert source_fingerprint(first) != source_fingerprint(second)


def test_content_overrides_accept_only_bounded_harmless_presentation_text():
    """Identity and academic blocks must never become client-writable."""
    accepted = ReportDraftContentSerializer(
        data={
            "content_overrides": {
                "manager_comment": "پیشرفت پایدار است.",
                "family_recommendations": "تمرین روزانه ادامه یابد.",
                "supplemental_text": "جلسه اولیا برگزار شد.",
                "display_title": "کارنامه رسمی",
                "footer_text": "نسخه مدرسه",
            }
        }
    )
    assert accepted.is_valid(), accepted.errors

    for forbidden in ("student_identity", "academic_summary", "scores", "rank"):
        serializer = ReportDraftContentSerializer(
            data={"content_overrides": {forbidden: "client supplied"}}
        )
        assert not serializer.is_valid()

    too_long = ReportDraftContentSerializer(
        data={"content_overrides": {"display_title": "x" * 121}}
    )
    assert not too_long.is_valid()


@pytest.mark.django_db
def test_family_context_excludes_raw_risk_internal_and_expired_recommendations(base_data):
    """A family snapshot may contain only current approved parent/student text."""
    from hamamooz.apps.reports.services import build_family_safe_context

    enrollment = base_data["enrollments"][0]
    common = {
        "organization": base_data["organization"],
        "school": base_data["school1"],
        "enrollment": enrollment,
        "rule_version": 1,
        "priority": Recommendation.Priority.MEDIUM,
        "reason_snapshot": {"raw_risk": "must not leak"},
        "generated_text": "internal generated text",
        "approved_text": "متن تأییدشده خانواده",
        "status": Recommendation.Status.APPROVED,
        "approved_at": timezone.now(),
    }
    visible = Recommendation.objects.create(
        **common, audience=Recommendation.Audience.PARENT, rule_code="family-current"
    )
    Recommendation.objects.create(
        **common,
        audience=Recommendation.Audience.PARENT,
        rule_code="family-expired",
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    Recommendation.objects.create(
        **common, audience=Recommendation.Audience.TEACHER, rule_code="internal-teacher"
    )
    Recommendation.objects.create(
        **{
            **common,
            "approved_text": "",
            "approved_at": None,
            "status": Recommendation.Status.PENDING_REVIEW,
        },
        audience=Recommendation.Audience.STUDENT,
        rule_code="unapproved-student",
    )

    context = build_family_safe_context(enrollment)

    assert "analytics_signals" not in context
    assert "behavior_events" not in context
    assert context["approved_recommendations"] == [
        {"id": str(visible.id), "audience": "parent", "approved_text": "متن تأییدشده خانواده"}
    ]
    serialized = repr(context)
    assert "raw_risk" not in serialized
    assert "internal generated text" not in serialized


def test_all_seven_templates_render_rtl_with_their_official_page_size_and_svg():
    """A wrong selector or shared fallback must not silently render the wrong family."""
    from hamamooz.apps.reports.services import REPORT_CARD_LAYOUTS, render_report_html

    for layout_key, config in REPORT_CARD_LAYOUTS.items():
        html = render_report_html(_minimal_snapshot(layout_key))
        assert '<html lang="fa" dir="rtl">' in html
        assert f'data-layout="{layout_key}"' in html
        assert f"size: {'A3 landscape' if config['page_size'] == 'a3_landscape' else 'A4 portrait'};" in html
        if layout_key.startswith("analytical_"):
            assert "<svg" in html


@pytest.mark.parametrize(
    "layout_key",
    [
        "analytical_term_1",
        "analytical_term_2",
        "analytical_annual",
        "final_term_1",
        "final_term_2",
        "final_annual",
    ],
)
def test_all_academic_templates_respect_three_independent_rank_visibility_settings(layout_key):
    """Every academic layout must show only explicitly enabled rank scopes."""
    from hamamooz.apps.reports.services import render_report_html

    snapshot = _minimal_snapshot(layout_key)
    if layout_key.endswith("annual"):
        snapshot["period"]["type"] = "annual"
    report = snapshot["reports"][0]
    report["rank_visibility"] = {"class": True, "grade": True, "school": True}
    html = render_report_html(snapshot)
    assert "رتبه کلاس" in html and "20" in html
    assert "رتبه پایه" in html and "60" in html
    assert "رتبه مدرسه" in html and "180" in html

    report["rank_visibility"] = {"class": True, "grade": False, "school": False}
    html = render_report_html(snapshot)
    assert "رتبه کلاس" in html
    assert "رتبه پایه" not in html
    assert "رتبه مدرسه" not in html


@pytest.mark.parametrize(
    "layout_key",
    [
        "analytical_term_1",
        "analytical_term_2",
        "analytical_annual",
        "final_term_1",
        "final_term_2",
        "final_annual",
        "summer_report",
    ],
)
def test_each_report_layout_produces_real_pdf_with_correct_page_dimensions(layout_key):
    """Official output must be real PDF with A3 landscape or A4 portrait media."""
    from hamamooz.apps.reports.services import render_report_pdf

    snapshot = _minimal_snapshot(layout_key)
    if layout_key.endswith("annual"):
        snapshot["period"]["type"] = "annual"
    elif layout_key == "summer_report":
        snapshot["period"]["type"] = "summer"
    payload = render_report_pdf(snapshot)

    assert payload.startswith(b"%PDF-")
    media_box = re.search(
        rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", payload
    )
    assert media_box is not None
    width, height = map(float, media_box.groups())
    assert width == pytest.approx(1190.55 if layout_key.startswith("analytical_") else 595.28, abs=1)
    assert height == pytest.approx(841.89, abs=1)


@pytest.mark.parametrize(
    "layout_key",
    [
        "analytical_term_1",
        "analytical_term_2",
        "analytical_annual",
        "final_term_1",
        "final_term_2",
        "final_annual",
        "summer_report",
    ],
)
def test_editable_docx_contains_snapshot_text_and_required_nonofficial_notice(layout_key):
    """The Word download must be editable content, not an image/PDF wrapper."""
    from docx import Document

    from hamamooz.apps.reports.services import render_report_docx

    snapshot = _minimal_snapshot(layout_key)
    if layout_key == "summer_report":
        snapshot["period"]["type"] = "summer"
    payload = render_report_docx(snapshot)
    width = Document(BytesIO(payload)).sections[0].page_width.cm
    with ZipFile(BytesIO(payload)) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    assert "دانش‌آموز نمونه" in xml
    assert "نسخه قابل ویرایش — اعتبار نهایی با PDF آرشیوشده سامانه" in xml
    assert "ریاضی" in xml
    assert "w:bidi" in xml
    assert width == pytest.approx(42 if layout_key.startswith("analytical_") else 21, abs=0.1)


def test_annual_html_and_docx_show_both_term_scores():
    """An annual weighted average must remain explainable from its two inputs."""
    from hamamooz.apps.reports.services import render_report_docx, render_report_html

    snapshot = _minimal_snapshot("final_annual")
    snapshot["period"] = {"type": "annual", "label": "۱۴۰۵-۱۴۰۶"}
    html = render_report_html(snapshot)
    assert "نمره نوبت اول" in html
    assert "نمره نوبت دوم" in html
    assert "17.00" in html and "18.00" in html
    with ZipFile(BytesIO(render_report_docx(snapshot))) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    assert "نوبت اول" in xml and "نوبت دوم" in xml
    assert "17.00" in xml and "18.00" in xml


def test_summer_docx_without_threshold_omits_every_pass_fail_label():
    """A null threshold must not imply or display any summer pass state."""
    from hamamooz.apps.reports.services import render_report_docx, render_report_html

    snapshot = _minimal_snapshot("summer_report")
    snapshot["period"] = {"type": "summer", "label": "تابستان"}
    report = snapshot["reports"][0]
    report["show_status"] = False
    report["pass_threshold"] = None
    report["summary"]["status_label"] = ""
    report["rank_visibility"] = {"class": False, "grade": False, "school": False}
    for subject in report["subjects"]:
        subject["passed"] = None
    html = render_report_html(snapshot)
    assert "کارنامه دوره تابستان" in html
    assert "آزمون جامع تابستان" in html
    assert "وضعیت" not in html
    assert "ضریب" not in html
    with ZipFile(BytesIO(render_report_docx(snapshot))) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    assert "کارنامه دوره تابستان" in xml
    assert "آزمون جامع تابستان" in xml
    assert "وضعیت" not in xml
    assert "ضریب" not in xml
    assert "نتیجه" not in xml
    assert "قبول" not in xml
    assert "مردود" not in xml


@pytest.mark.django_db
def test_completed_archive_snapshot_is_immutable_and_has_nullable_safe_annual_period(base_data):
    """Completed official meaning must survive later model saves and a null term."""
    archive = ReportArchive.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        term=None,
        layout_key="final_annual",
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        status=ReportArchive.Status.COMPLETED,
        enrollment=base_data["enrollments"][0],
        requested_by=base_data["manager"],
        snapshot={"average": "17.00"},
        source_fingerprint="a" * 64,
        tracking_code="RC-1405-000001",
        report_version=1,
    )
    assert archive.period_type == "annual"
    assert archive.period_label == base_data["year"].title

    archive.snapshot = {"average": "20.00"}
    with pytest.raises(ValidationError):
        archive.save()


@pytest.mark.django_db
def test_report_draft_preview_shows_incomplete_warning_without_issuing_archive(
    api_client, base_data
):
    """Preview is tenant-scoped/read-only and cannot skip approval or readiness."""
    template = ReportTemplate.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        code="preview-only-final-term",
        title="کارنامه نهایی نوبت اول",
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        layout_key="final_term_1",
        blocks=["student_identity", "academic_summary", "signatures"],
    )
    api_client.force_authenticate(base_data["manager"])
    headers = {"HTTP_X_SCHOOL_ID": str(base_data["school1"].id)}
    created = api_client.post(
        "/api/v1/reports/drafts/",
        {
            "template": str(template.id),
            "term": str(base_data["term"].id),
            "enrollment": str(base_data["enrollments"][0].id),
        },
        format="json",
        **headers,
    )
    assert created.status_code == 201, created.data

    response = api_client.get(
        f"/api/v1/reports/drafts/{created.data['id']}/preview/", **headers
    )

    assert response.status_code == 200
    assert 'data-layout="final_term_1"' in response.data["html"]
    assert response.data["warnings"]
    assert ReportDraft.objects.get(pk=created.data["id"]).status == ReportDraft.Status.DRAFT
    assert not ReportArchive.objects.filter(layout_key="final_term_1").exists()


@pytest.mark.django_db
def test_new_official_family_requires_approval_and_rejects_stale_fingerprint(
    api_client, base_data
):
    """A locked score mutation after submission must prevent human approval."""
    assessment = _locked_term_scores(base_data)
    template = ReportTemplate.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        code="official-final-term-one",
        title="کارنامه نهایی نوبت اول",
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        layout_key="final_term_1",
        blocks=["student_identity", "academic_summary", "signatures"],
    )
    api_client.force_authenticate(base_data["manager"])
    headers = {"HTTP_X_SCHOOL_ID": str(base_data["school1"].id)}
    created = api_client.post(
        "/api/v1/reports/drafts/",
        {
            "template": str(template.id),
            "term": str(base_data["term"].id),
            "enrollment": str(base_data["enrollments"][0].id),
        },
        format="json",
        **headers,
    )
    assert created.status_code == 201, created.data
    draft_id = created.data["id"]
    submitted = api_client.post(f"/api/v1/reports/drafts/{draft_id}/submit/", {}, **headers)
    assert submitted.status_code == 200, submitted.data
    assert ReportArchive.objects.filter(layout_key="final_term_1").count() == 0

    score = Score.objects.get(
        assessment=assessment, enrollment=base_data["enrollments"][0]
    )
    score.value = Decimal("19")
    score.save(update_fields=["value", "updated_at"])
    rejected = api_client.post(f"/api/v1/reports/drafts/{draft_id}/approve/", {}, **headers)
    assert rejected.status_code == 409
    assert ReportDraft.objects.get(pk=draft_id).status == ReportDraft.Status.SUBMITTED


@pytest.mark.django_db
def test_draft_create_cannot_escape_explicit_selected_school(api_client, base_data):
    """Having a second-school role must not override the request's selected tenant scope."""
    RoleAssignment.objects.create(
        user=base_data["manager"],
        organization=base_data["organization"],
        school=base_data["school2"],
        role=Role.SCHOOL_MANAGER,
    )
    template = ReportTemplate.objects.create(
        organization=base_data["organization"],
        school=base_data["school2"],
        code="school-two-class-report",
        title="School two report",
        report_type=ReportArchive.ReportType.CLASS_REPORT_CARDS,
        layout_key="final_term_1",
        blocks=["student_identity", "academic_summary"],
    )
    api_client.force_authenticate(base_data["manager"])
    response = api_client.post(
        "/api/v1/reports/drafts/",
        {
            "template": str(template.id),
            "term": str(base_data["term"].id),
            "class_section": str(base_data["class2"].id),
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert response.status_code == 400
    assert ReportDraft.objects.count() == 0


@pytest.mark.django_db
def test_school_manager_cannot_create_or_patch_organization_wide_template(
    api_client, base_data
):
    """A school role must not mutate a shared template consumed by other schools."""
    api_client.force_authenticate(base_data["manager"])
    headers = {"HTTP_X_SCHOOL_ID": str(base_data["school1"].id)}
    created = api_client.post(
        "/api/v1/reports/templates/",
        {
            "organization": str(base_data["organization"].id),
            "school": None,
            "code": "shared-unsafe",
            "title": "Shared unsafe",
            "report_type": ReportArchive.ReportType.STUDENT_REPORT_CARD,
            "layout_key": "final_term_1",
            "blocks": ["student_identity", "academic_summary"],
        },
        format="json",
        **headers,
    )
    assert created.status_code == 400

    shared = ReportTemplate.objects.create(
        organization=base_data["organization"],
        school=None,
        code="existing-shared",
        title="Existing shared",
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        layout_key="final_term_1",
        blocks=["student_identity", "academic_summary"],
    )
    patched = api_client.patch(
        f"/api/v1/reports/templates/{shared.id}/",
        {"title": "Manager changed it"},
        format="json",
        **headers,
    )
    assert patched.status_code == 400
    takeover = api_client.patch(
        f"/api/v1/reports/templates/{shared.id}/",
        {"school": str(base_data["school1"].id)},
        format="json",
        **headers,
    )
    assert takeover.status_code == 400
    shared.refresh_from_db()
    assert shared.title == "Existing shared"
    assert shared.school_id is None
