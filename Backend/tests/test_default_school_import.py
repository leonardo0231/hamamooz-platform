import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from hamamooz.apps.imports.models import ImportJob


@pytest.fixture
def besat_school(base_data):
    school = base_data["school1"]
    school.name = "بعثت"
    school.save(update_fields=["name"])
    return school


@pytest.fixture
def sample_excel():
    return SimpleUploadedFile(
        "sample.xlsx",
        b"fixture workbook bytes",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@pytest.mark.django_db
def test_import_without_school_uses_besat(
    api_client,
    base_data,
    besat_school,
    sample_excel,
):
    api_client.force_authenticate(base_data["manager"])

    response = api_client.post(
        "/api/v1/imports/",
        {
            "source_file": sample_excel,
            "import_type": ImportJob.ImportType.COMPREHENSIVE_SCHOOL,
        },
        format="multipart",
    )

    assert response.status_code == 201

    job = ImportJob.objects.get(pk=response.data["id"])

    assert job.school == besat_school


@pytest.mark.django_db
def test_import_honors_explicit_school(api_client, base_data, sample_excel):
    api_client.force_authenticate(base_data["teacher2"])

    response = api_client.post(
        "/api/v1/imports/",
        {
            "school": str(base_data["school2"].id),
            "source_file": sample_excel,
            "import_type": ImportJob.ImportType.COMPREHENSIVE_SCHOOL,
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert ImportJob.objects.get(pk=response.data["id"]).school == base_data["school2"]


@pytest.mark.django_db
def test_import_without_named_default_falls_back_to_first_accessible_school(
    api_client, base_data, sample_excel
):
    api_client.force_authenticate(base_data["manager"])

    response = api_client.post(
        "/api/v1/imports/",
        {
            "source_file": sample_excel,
            "import_type": ImportJob.ImportType.COMPREHENSIVE_SCHOOL,
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert ImportJob.objects.get(pk=response.data["id"]).school == base_data["school1"]
