from datetime import date
from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from openpyxl import load_workbook

from hamamooz.apps.evaluations.models import MonthlyEvaluation
from hamamooz.apps.imports.comprehensive_template import build_comprehensive_school_template
from hamamooz.apps.imports.models import ImportJob
from hamamooz.apps.imports.pipeline import process_import_job
from hamamooz.apps.imports.serializers import uploaded_file_checksum
from hamamooz.apps.students.models import Enrollment, Student


def _sample_like_workbook(base_data):
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

    evaluations["I5"] = 5
    evaluations["AV5"] = 20
    evaluations["CP5"] = "نمونه فایل عملیاتی"

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _create_job(base_data, payload):
    source = ContentFile(payload, name="sample-like.xlsx")
    checksum = uploaded_file_checksum(source)
    return ImportJob.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        import_type=ImportJob.ImportType.COMPREHENSIVE_SCHOOL,
        source_file=source,
        checksum=checksum,
        requested_by=base_data["manager"],
    )


@pytest.mark.django_db
def test_comprehensive_import_accepts_sample_conventions_without_editing_excel(base_data):
    base_data["school1"].is_active = False
    base_data["school1"].save(update_fields=["is_active"])
    base_data["year"].is_active = False
    base_data["year"].save(update_fields=["is_active"])
    base_data["grade"].title = "پایه 7"
    base_data["grade"].is_active = False
    base_data["grade"].save(update_fields=["title", "is_active"])

    job = _create_job(base_data, _sample_like_workbook(base_data))
    process_import_job(job.id)
    job.refresh_from_db()

    assert job.status == ImportJob.Status.COMPLETED, job.errors
    student = Student.objects.get(organization=base_data["organization"], national_id="0960715363")
    assert student.birth_date == date(2014, 1, 9)

    enrollment = Enrollment.objects.get(student=student, academic_year=base_data["year"])
    assert enrollment.school == base_data["school1"]
    assert enrollment.class_section.code == "701"
    assert enrollment.student_number == "شماره/1"

    evaluation = MonthlyEvaluation.objects.get(enrollment=enrollment, month_no=1)
    assert evaluation.metric_scores.get(metric_code="ART_06").value == 5

    warning_codes = {warning["code"] for warning in job.result_summary["normalization_warnings"]}
    assert {
        "selected_school_inactive",
        "school_code_ignored",
        "academic_year_inactive",
        "grade_inactive",
        "national_id_normalized",
        "jalali_birth_date_converted",
        "metric_score_scaled",
    }.issubset(warning_codes)
    assert job.result_summary["warning_count"] >= 7
