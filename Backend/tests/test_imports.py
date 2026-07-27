from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from openpyxl import Workbook

from hamamooz.apps.academics.models import Assessment, Score
from hamamooz.apps.imports.models import ImportJob
from hamamooz.apps.imports.serializers import uploaded_file_checksum
from hamamooz.apps.imports.services import (
    EXPECTED_HEADERS,
    mark_import_job_failed,
    process_import_job,
)
from hamamooz.apps.students.models import Student


def workbook_bytes(rows, import_type=ImportJob.ImportType.STUDENTS):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(EXPECTED_HEADERS[import_type])
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def create_job(base_data, rows, import_type=ImportJob.ImportType.STUDENTS):
    payload = workbook_bytes(rows, import_type)
    source = ContentFile(payload, name=f"{import_type}.xlsx")
    checksum = uploaded_file_checksum(source)
    return ImportJob.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        import_type=import_type,
        source_file=source,
        checksum=checksum,
        requested_by=base_data["manager"],
    )


@pytest.mark.django_db
def test_import_is_atomic_when_one_row_is_invalid(base_data):
    before = Student.objects.count()
    job = create_job(
        base_data,
        [
            ["0012345680", "سارا", "احمدی", "2012-03-04", "female"],
            ["invalid", "رضا", "احمدی", "2012-03-05", "male"],
        ],
    )
    process_import_job(job.id)
    job.refresh_from_db()
    assert job.status == ImportJob.Status.FAILED
    assert job.error_count == 1
    assert Student.objects.count() == before


@pytest.mark.django_db
def test_valid_student_import_completes(base_data):
    job = create_job(
        base_data,
        [["0012345680", "سارا", "احمدی", "2012-03-04", "female"]],
    )
    result = process_import_job(job.id)
    job.refresh_from_db()
    assert result == job
    assert job.status == ImportJob.Status.COMPLETED
    assert job.total_rows == 1
    assert job.successful_rows == 1
    assert Student.objects.filter(national_id="0012345680").exists()


@pytest.mark.django_db
def test_student_import_handles_mvp_volume(base_data):
    row_count = 2_000
    rows = [
        [f"{1_000_000_000 + index:010d}", "دانش‌آموز", str(index), "2012-03-04", "female"]
        for index in range(row_count)
    ]
    job = create_job(base_data, rows)

    process_import_job(job.id)
    job.refresh_from_db()

    assert job.status == ImportJob.Status.COMPLETED
    assert job.successful_rows == row_count
    assert Student.objects.filter(organization=base_data["organization"]).count() == row_count + 2


@pytest.mark.django_db
def test_corrupt_workbook_fails_as_a_job_instead_of_crashing(base_data):
    source = ContentFile(b"not-an-xlsx", name="students.xlsx")
    checksum = uploaded_file_checksum(source)
    job = ImportJob.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        import_type=ImportJob.ImportType.STUDENTS,
        source_file=source,
        checksum=checksum,
        requested_by=base_data["manager"],
    )
    process_import_job(job.id)
    job.refresh_from_db()
    assert job.status == ImportJob.Status.FAILED
    assert job.error_count == 1


@pytest.mark.django_db
def test_valid_enrollment_import_completes(base_data):
    Student.objects.create(
        organization=base_data["organization"],
        national_id="0012345680",
        first_name="ثبت‌نام",
        last_name="اکسل",
        birth_date=date(2012, 3, 4),
        gender=Student.Gender.FEMALE,
    )
    job = create_job(
        base_data,
        [
            [
                "0012345680",
                base_data["year"].code,
                base_data["grade"].code,
                base_data["class1"].code,
                "excel-103",
                "2026-09-23",
            ]
        ],
        ImportJob.ImportType.ENROLLMENTS,
    )

    process_import_job(job.id)
    job.refresh_from_db()

    assert job.status == ImportJob.Status.COMPLETED
    assert job.successful_rows == 1
    assert base_data["class1"].enrollments.filter(student_number="excel-103").exists()


@pytest.mark.django_db
def test_enrollment_import_is_atomic_when_capacity_is_insufficient(base_data):
    base_data["class1"].capacity = 2
    base_data["class1"].save(update_fields=["capacity"])
    Student.objects.create(
        organization=base_data["organization"],
        national_id="0012345681",
        first_name="ظرفیت",
        last_name="اکسل",
        birth_date=date(2012, 3, 4),
        gender=Student.Gender.FEMALE,
    )
    job = create_job(
        base_data,
        [
            [
                "0012345681",
                base_data["year"].code,
                base_data["grade"].code,
                base_data["class1"].code,
                "excel-full",
                "2026-09-23",
            ]
        ],
        ImportJob.ImportType.ENROLLMENTS,
    )

    process_import_job(job.id)
    job.refresh_from_db()

    assert job.status == ImportJob.Status.FAILED
    assert not base_data["class1"].enrollments.filter(student_number="excel-full").exists()


@pytest.mark.django_db
def test_valid_score_import_completes(base_data):
    assessment = Assessment.objects.create(
        course_offering=base_data["offering1"],
        assessment_type=base_data["continuous"],
        title="ورود نمره اکسل",
        assessment_date=date(2026, 10, 10),
        max_score=Decimal("20"),
        created_by=base_data["teacher1"],
    )
    rows = [
        [str(assessment.id), student.national_id, value, "present", ""]
        for student, value in zip(base_data["students"], [18, 16], strict=True)
    ]
    job = create_job(base_data, rows, ImportJob.ImportType.SCORES)

    process_import_job(job.id)
    job.refresh_from_db()

    assert job.status == ImportJob.Status.COMPLETED
    assert job.successful_rows == 2
    assert Score.objects.filter(assessment=assessment).count() == 2


@pytest.mark.django_db
def test_io_failure_returns_job_to_queue_for_task_retry(base_data, monkeypatch):
    job = create_job(
        base_data,
        [["0012345682", "خطا", "فایل", "2012-03-04", "female"]],
    )

    def raise_io_error(_job):
        raise OSError("storage unavailable")

    monkeypatch.setattr("hamamooz.apps.imports.services._load_rows", raise_io_error)
    with pytest.raises(OSError):
        process_import_job(job.id)

    job.refresh_from_db()
    assert job.status == ImportJob.Status.QUEUED
    mark_import_job_failed(job.id, OSError("storage unavailable"))
    job.refresh_from_db()
    assert job.status == ImportJob.Status.FAILED
    assert job.error_count == 1


@pytest.mark.django_db
def test_active_duplicate_import_is_blocked_by_database(base_data):
    first = create_job(
        base_data,
        [["0012345683", "تکرار", "فایل", "2012-03-04", "female"]],
    )
    duplicate_source = ContentFile(
        workbook_bytes([["0012345683", "تکرار", "فایل", "2012-03-04", "female"]]),
        name="duplicate.xlsx",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        ImportJob.objects.create(
            organization=base_data["organization"],
            school=base_data["school1"],
            import_type=ImportJob.ImportType.STUDENTS,
            source_file=duplicate_source,
            checksum=first.checksum,
            requested_by=base_data["manager"],
        )
