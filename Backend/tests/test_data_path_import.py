from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook
from PIL import Image

from hamamooz.apps.evaluations.models import AssessmentRecord
from hamamooz.apps.imports.comprehensive_template import build_comprehensive_school_template
from hamamooz.apps.imports.models import DataPathImport
from hamamooz.apps.imports.services.data_path import process_data_path_import
from hamamooz.apps.reports.models import ReportArchive, ReportBatch
from hamamooz.apps.reports.services import build_monthly_analytical_snapshot, render_report_batch
from hamamooz.apps.students.models import Enrollment, Student


def _data_workbook(base_data):
    workbook = load_workbook(build_comprehensive_school_template())
    classes = workbook["کلاس‌بندی"]
    students = workbook["دانش‌آموزان"]
    evaluations = workbook["ثبت اطلاعات"]

    classes["B5"] = "101"
    classes["C5"] = base_data["year"].code
    classes["D5"] = "701"
    classes["E5"] = "شهید سلیمانی یک"
    classes["F5"] = "هفتم"
    classes["G5"] = 40

    students["C5"] = "960715363"
    students["D5"] = "شماره/۱"
    students["E5"] = "رضا"
    students["F5"] = "ابراهیمی"
    students["G5"] = "پسر"
    students["H5"] = "1392/10/19"
    students["I5"] = "701"

    # The operational Data workbooks use more than the legacy integer 0..5
    # rubric.  Keep one value from each relevant category in this fixture.
    evaluations["G5"] = 16.7
    evaluations["H5"] = -2.5
    evaluations["I5"] = "ندارد"
    evaluations["J5"] = 4

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _jpeg_bytes():
    output = BytesIO()
    Image.new("RGB", (24, 32), (30, 120, 180)).save(output, format="JPEG")
    return output.getvalue()


@pytest.mark.django_db
def test_data_path_records_workbooks_photos_and_monthly_report_context(
    base_data, tmp_path, monkeypatch
):
    data_root = tmp_path / "Data"
    excel_root = data_root / "Excel"
    photo_root = data_root / "Photo" / "8" / "کدملی"
    excel_root.mkdir(parents=True)
    photo_root.mkdir(parents=True)
    (excel_root / "registrar.xlsx").write_bytes(_data_workbook(base_data))
    (photo_root / "0960715363.jpg").write_bytes(_jpeg_bytes())

    monkeypatch.setattr(
        "hamamooz.apps.reports.tasks.generate_report_batch_task.delay",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        "hamamooz.apps.reports.services.render_report_pdf",
        lambda _snapshot: b"%PDF-1.7 test report",
    )
    run = DataPathImport.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        requested_by=base_data["manager"],
        source_root=str(data_root),
        report_month=1,
        generate_reports=True,
    )

    result = process_data_path_import(run.id)
    result.refresh_from_db()

    assert result.status == DataPathImport.Status.COMPLETED, result.errors
    assert result.manifest["counts"]["workbooks"] == 1
    assert result.result_summary["excel_jobs_completed"] == 1
    assert result.result_summary["photo_summary"]["matched"] == 1

    student = Student.objects.get(
        organization=base_data["organization"], national_id="0960715363"
    )
    assert student.photo
    assert student.photo.read() == _jpeg_bytes()

    records = AssessmentRecord.objects.filter(student=student).select_related("indicator")
    by_code = {record.indicator.code: record for record in records}
    assert by_code["EDU_01"].score == Decimal("16.70")
    assert by_code["EDU_01"].raw_value == "16.7"
    assert by_code["EDU_01"].value_kind == "score_20"
    assert by_code["EDU_02"].score == Decimal("-2.50")
    assert by_code["EDU_02"].value_kind == "delta"
    assert by_code["EDU_03"].score is None
    assert by_code["EDU_03"].raw_value == "ندارد"
    assert by_code["EDU_03"].status == "not_recorded"
    assert by_code["EDU_04"].value_kind == "rubric_5"

    batch = ReportBatch.objects.get(
        school=base_data["school1"], report_mode=ReportBatch.ReportMode.DATA_MONTHLY
    )
    assert batch.term is None
    assert batch.month_no == 1
    assert batch.total_count == 3
    assert batch.items.filter(enrollment__student=student).count() == 1

    enrollment = Enrollment.objects.get(student=student, academic_year=base_data["year"])
    snapshot = build_monthly_analytical_snapshot(enrollment, 1)
    report = snapshot["reports"][0]
    assert report["student"]["photo_url"] == student.photo.url
    latest = report["product_context"]["latest_evaluation"]
    metric_rows = {row["code"]: row for row in latest["metrics"]}
    assert metric_rows["EDU_01"]["raw_value"] == "16.7"
    assert metric_rows["EDU_02"]["value_kind"] == "delta"
    assert metric_rows["EDU_03"]["status"] == "not_recorded"

    rendered = render_report_batch(batch.id)
    assert rendered.status == ReportBatch.Status.COMPLETED
    assert rendered.completed_count == rendered.total_count == 3
    assert rendered.zip_file
    assert ReportArchive.objects.filter(
        report_mode=ReportArchive.ReportMode.DATA_MONTHLY,
        month_no=1,
        term__isnull=True,
        status=ReportArchive.Status.COMPLETED,
    ).count() == 3


@pytest.mark.django_db
def test_data_path_api_queues_only_the_configured_server_root(
    api_client, base_data, settings, tmp_path, monkeypatch
):
    data_root = tmp_path / "Data"
    data_root.mkdir()
    settings.DATA_ROOT = data_root
    monkeypatch.setattr(
        "hamamooz.apps.imports.views.process_data_path_import_task.delay",
        lambda *_args: None,
    )
    api_client.force_authenticate(base_data["manager"])
    scope = {"HTTP_X_SCHOOL_ID": str(base_data["school1"].id)}

    response = api_client.post(
        "/api/v1/imports/from-data-path/",
        {"school": str(base_data["school1"].id), "generate_reports": False},
        format="json",
        **scope,
    )
    assert response.status_code == 202
    assert response.data["source_root"] == str(data_root)
    assert DataPathImport.objects.get(pk=response.data["id"]).generate_reports is False

    rejected = api_client.post(
        "/api/v1/imports/from-data-path/",
        {
            "school": str(base_data["school1"].id),
            "source_root": str(tmp_path / "another-data-root"),
        },
        format="json",
        **scope,
    )
    assert rejected.status_code == 400
