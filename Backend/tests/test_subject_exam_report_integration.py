from decimal import Decimal

import pytest
from django.test import override_settings

from hamamooz.apps.academics.models import TermResult
from hamamooz.apps.evaluations.models import MetricScore, MonthlyEvaluation
from hamamooz.apps.reports.services import build_student_snapshot
from hamamooz.apps.reports.subject_exam_integration import (
    SUBJECT_EXAM_RESULT_PROVIDER_SETTING,
)


def _subject_exam_provider(*, enrollment):
    return [
        {
            "id": "summer-row-1",
            "enrollment_id": str(enrollment.id),
            "exam_period": "summer",
            "subject_name": "ریاضی",
            "grade_name": "هفتم",
            "class_name": "7-a",
            "question_count": 20,
            "correct_count": 18,
            "wrong_count": 1,
            "blank_count": 1,
            "percentage": "90.00",
            "highest_percentage": "98.50",
            "rank": 3,
            "t_score": "612.5",
            "overall_rank": 8,
            "score": "18",
            "final_score": "18.5",
            "source_file": "کارنامه تفصیلی آزمون تابستانه هفتم.xlsx",
            "source_row": 12,
            "raw_values": {"نمره نهائی": "18.5", "درصد": "90.00"},
        }
    ]


@pytest.mark.django_db
def test_monthly_preview_exposes_subject_exam_rows_as_a_separate_collection(api_client, base_data):
    evaluation = MonthlyEvaluation.objects.create(
        enrollment=base_data["enrollments"][0],
        month_no=3,
        framework_version="2.0",
        recorded_by=base_data["manager"],
    )
    MetricScore.objects.create(evaluation=evaluation, metric_code="EDU_01", value=5)

    api_client.force_authenticate(base_data["manager"])
    with override_settings(**{SUBJECT_EXAM_RESULT_PROVIDER_SETTING: _subject_exam_provider}):
        response = api_client.post(
            "/api/v1/reports/monthly-preview/",
            {"enrollment": str(evaluation.enrollment_id), "month_no": 3},
            format="json",
            HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
        )

    assert response.status_code == 200, response.data
    assert response.data["summer_subject_results"] == [
        {
            "id": "summer-row-1",
            "enrollment_id": str(evaluation.enrollment_id),
            "exam_key": "summer",
            "exam_title": "آزمون تابستانه",
            "subject_code": "",
            "subject_title": "ریاضی",
            "grade": "هفتم",
            "class_code": "7-a",
            "question_count": 20,
            "correct_count": 18,
            "wrong_count": 1,
            "blank_count": 1,
            "percent": 90.0,
            "highest_percent": 98.5,
            "rank": 3,
            "t_score": 612.5,
            "overall_rank": 8,
            "score": 18.0,
            "final_score": 18.5,
            "source_file": "کارنامه تفصیلی آزمون تابستانه هفتم.xlsx",
            "source_row": 12,
            "raw": {"نمره نهائی": "18.5", "درصد": "90.00"},
        }
    ]
    assert "subjects" not in response.data
    assert all(item["code"] != "ریاضی" for item in response.data["metrics"])


@pytest.mark.django_db
def test_student_snapshot_keeps_subject_exam_rows_outside_official_subjects(
    base_data,
):
    enrollment = base_data["enrollments"][0]
    TermResult.objects.create(
        enrollment=enrollment,
        term=base_data["term"],
        average=Decimal("17.00"),
        class_rank=1,
        passed=True,
        formula_version="mvp-v1",
    )

    with override_settings(**{SUBJECT_EXAM_RESULT_PROVIDER_SETTING: _subject_exam_provider}):
        snapshot = build_student_snapshot(enrollment, base_data["term"], recalculate=False)

    assert snapshot["summer_subject_results"][0]["subject_title"] == "ریاضی"
    assert all("final_score" not in subject for subject in snapshot["subjects"])


@pytest.mark.django_db
def test_student_360_academics_exposes_the_same_separate_contract(api_client, base_data):
    student = base_data["students"][0]
    api_client.force_authenticate(base_data["manager"])

    with override_settings(**{SUBJECT_EXAM_RESULT_PROVIDER_SETTING: _subject_exam_provider}):
        response = api_client.get(
            f"/api/v1/students/{student.id}/360/academics/",
            HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
        )

    assert response.status_code == 200, response.data
    assert response.data["summer_subject_results"][0]["exam_key"] == "summer"
    assert response.data["subject_results"] == []
