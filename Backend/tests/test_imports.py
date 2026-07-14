from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from openpyxl import Workbook

from hamamooz.apps.imports.models import ImportJob
from hamamooz.apps.imports.serializers import uploaded_file_checksum
from hamamooz.apps.imports.services import EXPECTED_HEADERS, process_import_job
from hamamooz.apps.students.models import Student


def workbook_bytes(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(EXPECTED_HEADERS[ImportJob.ImportType.STUDENTS])
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def create_job(base_data, rows):
    payload = workbook_bytes(rows)
    source = ContentFile(payload, name="students.xlsx")
    checksum = uploaded_file_checksum(source)
    return ImportJob.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        import_type=ImportJob.ImportType.STUDENTS,
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
    process_import_job(job.id)
    job.refresh_from_db()
    assert job.status == ImportJob.Status.COMPLETED
    assert job.successful_rows == 1
    assert Student.objects.filter(national_id="0012345680").exists()


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
