from pathlib import Path

path = Path("Backend/tests/test_api_workflows.py")
text = path.read_text()

text = text.replace(
    "from io import BytesIO\n\nimport pytest\nfrom django.core.files.uploadedfile import SimpleUploadedFile\nfrom django.core.management import call_command\nfrom openpyxl import Workbook, load_workbook\n",
    "from io import BytesIO\nfrom pathlib import Path\n\nimport pytest\nfrom django.conf import settings\nfrom django.core.files.uploadedfile import SimpleUploadedFile\nfrom openpyxl import load_workbook\n",
)
text = text.replace(
    "from hamamooz.apps.imports.models import ImportJob\nfrom hamamooz.apps.imports.services import EXPECTED_HEADERS\n",
    "from hamamooz.apps.imports.models import ImportJob\n",
)

start = text.index("def xlsx_upload(rows):")
end = text.index(
    "\n\n@pytest.mark.django_db\ndef test_import_template_download_is_authorized_valid_xlsx",
    start,
)
helper = '''def comprehensive_upload(base_data):
    template = (
        Path(settings.BASE_DIR)
        / "docs"
        / "import_templates"
        / "comprehensive_school_template.xlsx"
    )
    workbook = load_workbook(template)
    classes = workbook["کلاس‌بندی"]
    students = workbook["دانش‌آموزان"]
    evaluations = workbook["ثبت اطلاعات"]

    class_code = "7-api-import"
    classes["B5"] = base_data["school1"].code
    classes["C5"] = base_data["year"].code
    classes["D5"] = class_code
    classes["E5"] = "هفتم API Import"
    classes["F5"] = base_data["grade"].title
    classes["G5"] = 30

    students["B5"] = "1"
    students["C5"] = "0012345689"
    students["D5"] = "api-103"
    students["E5"] = "ایمپورت"
    students["F5"] = "API"
    students["G5"] = "دختر"
    students["H5"] = "2012-03-04"
    students["I5"] = class_code

    evaluations["C5"] = "1"
    evaluations["D5"] = "0012345689"
    evaluations["E5"] = "ایمپورت API"
    evaluations["F5"] = class_code
    evaluations["G5"] = 4

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return SimpleUploadedFile(
        "comprehensive_school.xlsx",
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
'''
text = text[:start] + helper + text[end:]

start = text.index(
    "@pytest.mark.django_db\ndef test_import_template_download_is_authorized_valid_xlsx"
)
end = text.index("\n\ndef create_assessment_via_api", start)
replacement = '''@pytest.mark.django_db
def test_import_template_download_is_authorized_valid_xlsx(api_client, base_data):
    url = "/api/v1/imports/templates/comprehensive_school/"

    unauthenticated = api_client.get(url)
    assert unauthenticated.status_code == 401

    api_client.force_authenticate(base_data["teacher1"])
    authenticated = api_client.get(url)
    assert authenticated.status_code == 200
    authenticated.close()

    api_client.force_authenticate(base_data["manager"])
    missing = api_client.get("/api/v1/imports/templates/not-a-template/")
    assert missing.status_code == 404

    response = api_client.get(url)
    payload = b"".join(response.streaming_content)
    assert response.status_code == 200
    assert response["Content-Type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response["Content-Disposition"] == (
        'attachment; filename="comprehensive_school_template.xlsx"'
    )
    assert len(payload) > 100
    assert payload.startswith(b"PK")
    workbook = load_workbook(BytesIO(payload), read_only=True)
    assert {"کلاس‌بندی", "دانش‌آموزان", "ثبت اطلاعات"}.issubset(workbook.sheetnames)
    workbook.close()
'''
text = text[:start] + replacement + text[end:]

start = text.index(
    "@pytest.mark.django_db\ndef test_import_create_duplicate_and_retry_api_paths"
)
end = text.index(
    "\n\n@pytest.mark.django_db\ndef test_report_preview_archive_and_download_api",
    start,
)
replacement = '''@pytest.mark.django_db
def test_import_create_duplicate_and_retry_api_paths(api_client, base_data):
    source = comprehensive_upload(base_data)
    source_bytes = source.read()
    source.seek(0)
    api_client.force_authenticate(base_data["manager"])
    response = api_client.post(
        "/api/v1/imports/",
        {
            "school": str(base_data["school1"].id),
            "import_type": ImportJob.ImportType.COMPREHENSIVE_SCHOOL,
            "source_file": source,
        },
        format="multipart",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert response.status_code == 201
    job = ImportJob.objects.get(pk=response.data["id"])

    duplicate = api_client.post(
        "/api/v1/imports/",
        {
            "school": str(base_data["school1"].id),
            "import_type": ImportJob.ImportType.COMPREHENSIVE_SCHOOL,
            "source_file": SimpleUploadedFile(
                "comprehensive_school.xlsx",
                source_bytes,
                content_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ),
        },
        format="multipart",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert duplicate.status_code == 400

    job.status = ImportJob.Status.FAILED
    job.save(update_fields=["status"])
    retry = api_client.post(
        f"/api/v1/imports/{job.id}/retry/",
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert retry.status_code == 200
    assert retry.data["status"] == ImportJob.Status.QUEUED
'''
text = text[:start] + replacement + text[end:]

path.write_text(text)
