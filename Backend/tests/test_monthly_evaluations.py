import pytest
from test_imports import create_job

from hamamooz.apps.evaluations.models import MetricScore, MonthlyEvaluation
from hamamooz.apps.imports.models import ImportJob
from hamamooz.apps.imports.services import process_import_job


def evaluation_row(base_data, metric_code, score, *, month_no=4, school_code=None):
    enrollment = base_data["enrollments"][0]
    return [
        "1.0",
        school_code or base_data["school1"].code,
        base_data["year"].code,
        base_data["class1"].code,
        enrollment.student_number,
        enrollment.student.national_id,
        month_no,
        metric_code,
        score,
        "ارزیابی مهر",
    ]


@pytest.mark.django_db
def test_monthly_evaluation_import_persists_and_updates_scores(base_data):
    job = create_job(
        base_data,
        [
            evaluation_row(base_data, "EDU_01", 4),
            evaluation_row(base_data, "EDU_02", 3),
            evaluation_row(base_data, "DEV_01", 5),
        ],
        ImportJob.ImportType.MONTHLY_EVALUATIONS,
    )

    process_import_job(job.id)
    job.refresh_from_db()

    assert job.status == ImportJob.Status.COMPLETED
    assert job.successful_rows == 3
    evaluation = MonthlyEvaluation.objects.get(enrollment=base_data["enrollments"][0], month_no=4)
    assert evaluation.note == "ارزیابی مهر"
    assert evaluation.source_import_job == job
    assert dict(evaluation.metric_scores.values_list("metric_code", "value")) == {
        "DEV_01": 5,
        "EDU_01": 4,
        "EDU_02": 3,
    }

    update_job = create_job(
        base_data,
        [evaluation_row(base_data, "EDU_01", 2)],
        ImportJob.ImportType.MONTHLY_EVALUATIONS,
    )
    process_import_job(update_job.id)

    assert MonthlyEvaluation.objects.count() == 1
    assert MetricScore.objects.get(evaluation=evaluation, metric_code="EDU_01").value == 2


@pytest.mark.django_db
def test_monthly_evaluation_import_is_atomic_on_invalid_row(base_data):
    job = create_job(
        base_data,
        [
            evaluation_row(base_data, "EDU_01", 4),
            evaluation_row(base_data, "UNKNOWN", 3),
        ],
        ImportJob.ImportType.MONTHLY_EVALUATIONS,
    )

    process_import_job(job.id)
    job.refresh_from_db()

    assert job.status == ImportJob.Status.FAILED
    assert MonthlyEvaluation.objects.count() == 0
    assert job.errors[0]["row"] == 3


@pytest.mark.django_db
def test_monthly_evaluation_import_rejects_wrong_school_scope(base_data):
    job = create_job(
        base_data,
        [
            evaluation_row(
                base_data,
                "EDU_01",
                4,
                school_code=base_data["school2"].code,
            )
        ],
        ImportJob.ImportType.MONTHLY_EVALUATIONS,
    )

    process_import_job(job.id)
    job.refresh_from_db()

    assert job.status == ImportJob.Status.FAILED
    assert "شعبه انتخاب‌شده" in job.errors[0]["message"]
    assert MonthlyEvaluation.objects.count() == 0


@pytest.mark.django_db
def test_monthly_evaluation_api_is_scoped_and_returns_calculations(api_client, base_data):
    job = create_job(
        base_data,
        [
            evaluation_row(base_data, "EDU_01", 4),
            evaluation_row(base_data, "EDU_02", 3),
        ],
        ImportJob.ImportType.MONTHLY_EVALUATIONS,
    )
    process_import_job(job.id)
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        "/api/v1/monthly-evaluations/",
        {"enrollment__student": str(base_data["students"][0].id)},
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    result = response.data["results"][0]
    assert result["student"] == str(base_data["students"][0].id)
    assert result["month_no"] == 4
    assert result["overall_score"] == 14.0
    assert result["completion_percent"] == pytest.approx(2 / 74 * 100, abs=0.01)

    denied = api_client.get(
        "/api/v1/monthly-evaluations/",
        HTTP_X_SCHOOL_ID=str(base_data["school2"].id),
    )
    assert denied.status_code == 403
