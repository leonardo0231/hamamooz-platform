from types import SimpleNamespace

import pytest

from hamamooz.apps.evaluations.models import MetricScore, MonthlyEvaluation
from hamamooz.apps.reports.models import ReportArchive
from hamamooz.apps.reports.serializers import ReportArchiveSerializer


@pytest.fixture
def monthly_evaluation(base_data):
    evaluation = MonthlyEvaluation.objects.create(
        enrollment=base_data["enrollments"][0],
        month_no=3,
        framework_version="2.0",
        recorded_by=base_data["manager"],
    )
    MetricScore.objects.create(evaluation=evaluation, metric_code="EDU_01", value=5)
    MetricScore.objects.create(evaluation=evaluation, metric_code="DEV_01", value=3)
    return evaluation


@pytest.mark.django_db
def test_data_monthly_preview_uses_summer_period_title_and_explicit_contract(
    api_client, base_data, monthly_evaluation
):
    api_client.force_authenticate(base_data["manager"])

    response = api_client.post(
        "/api/v1/reports/monthly-preview/",
        {
            "enrollment": str(monthly_evaluation.enrollment_id),
            "month_no": 3,
            "source_file": "Data/Excel/701.xlsx",
            "source_row": 12,
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200, response.data
    assert response.data["report_mode"] == "data_monthly"
    assert response.data["month"] == {"no": 3, "title": "شهریور"}
    assert response.data["source_file"] == "Data/Excel/701.xlsx"
    assert response.data["source_row"] == 12
    assert response.data["organization"]["name"] == base_data["organization"].name
    assert response.data["school"]["name"] == (
        base_data["school1"].official_name or base_data["school1"].name
    )
    assert response.data["student"]["class_code"] == base_data["class1"].code
    assert response.data["completion_percent"] > 0
    assert response.data["monthly_scores"] == [
        {
            "month_no": 3,
            "overall_score": response.data["monthly_scores"][0]["overall_score"],
            "completion_percent": response.data["monthly_scores"][0]["completion_percent"],
            "completion_status": response.data["monthly_scores"][0]["completion_status"],
            "month_title": "شهریور",
        }
    ]
    assert {item["code"] for item in response.data["metrics"]} == {"EDU_01", "DEV_01"}
    assert response.data["missing_sections"] == [
        "attendance",
        "activities",
        "counselor_report",
        "official_subject_grades",
    ]


@pytest.mark.django_db
def test_data_monthly_archive_requires_month_and_provenance(
    api_client, base_data, monthly_evaluation
):
    payload = {
        "report_mode": ReportArchive.ReportMode.DATA_MONTHLY,
        "report_type": ReportArchive.ReportType.STUDENT_REPORT_CARD,
        "enrollment": str(monthly_evaluation.enrollment_id),
        "month_no": 3,
        "source_file": "Data/Excel/701.xlsx",
        "source_row": 12,
    }
    request = SimpleNamespace(user=base_data["manager"])
    serializer = ReportArchiveSerializer(data=payload, context={"request": request})

    assert serializer.is_valid(), serializer.errors
    archive = serializer.save()
    assert archive.term is None
    assert archive.month_title == "شهریور"
    assert archive.report_mode == ReportArchive.ReportMode.DATA_MONTHLY


@pytest.mark.django_db
def test_data_monthly_archive_rejects_term_or_missing_provenance(
    api_client, base_data, monthly_evaluation
):
    request = SimpleNamespace(user=base_data["manager"])
    serializer = ReportArchiveSerializer(
        data={
            "report_mode": ReportArchive.ReportMode.DATA_MONTHLY,
            "report_type": ReportArchive.ReportType.STUDENT_REPORT_CARD,
            "enrollment": str(monthly_evaluation.enrollment_id),
            "month_no": 3,
            "term": str(base_data["term"].id),
        },
        context={"request": request},
    )

    assert not serializer.is_valid()
    assert "source_file" in serializer.errors
