import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from django.core.files.base import ContentFile
from django.core.management import call_command
from PIL import Image

from hamamooz.apps.imports.services.photo_importer import StudentPhotoImporter


def jpeg_bytes(color):
    output = io.BytesIO()
    Image.new("RGB", (24, 32), color).save(output, format="JPEG")
    return output.getvalue()


def write_photo(path: Path, color=(20, 80, 140)):
    path.write_bytes(jpeg_bytes(color))


@pytest.mark.django_db
def test_directory_dry_run_reports_matches_without_writing(base_data, tmp_path):
    write_photo(tmp_path / "0012345678.jpg")
    write_photo(tmp_path / "0012345678 (2).jpg", color=(180, 40, 40))
    write_photo(tmp_path / "9999999999.jpg")
    write_photo(tmp_path / "not-a-national-id.jpg")

    result = StudentPhotoImporter(base_data["organization"]).import_directory(
        tmp_path,
        dry_run=True,
    )

    assert result["received"] == 4
    # Duplicate portraits are a hard review stop: the importer must not
    # silently choose whichever file happens to sort first.
    assert result["matched"] == 0
    assert result["missing_students"] == 1
    assert result["duplicates"] == 2
    assert result["duplicate_files"] == [
        "0012345678 (2).jpg",
        "0012345678.jpg",
    ]
    assert result["invalid_files"] == ["not-a-national-id.jpg"]
    assert not base_data["students"][0].photo


@pytest.mark.django_db
def test_existing_photo_requires_explicit_overwrite(base_data, tmp_path):
    student = base_data["students"][0]
    existing_payload = jpeg_bytes((1, 2, 3))
    student.photo.save("existing.jpg", ContentFile(existing_payload), save=True)
    write_photo(tmp_path / f"{student.national_id}.jpg", color=(200, 100, 20))

    importer = StudentPhotoImporter(base_data["organization"])
    preserved = importer.import_directory(tmp_path)
    student.refresh_from_db()
    assert preserved["matched"] == 0
    assert preserved["skipped_existing"] == 1
    assert student.photo.read() == existing_payload

    replaced = importer.import_directory(tmp_path, overwrite=True)
    student.refresh_from_db()
    assert replaced["matched"] == 1
    assert student.photo.read() != existing_payload


@pytest.mark.django_db
def test_photo_command_dry_run_emits_auditable_json(base_data, tmp_path):
    write_photo(tmp_path / f"{base_data['students'][0].national_id}.jpg")
    output = io.StringIO()

    call_command(
        "import_student_photos",
        "--organization-id",
        str(base_data["organization"].id),
        "--directory",
        str(tmp_path),
        "--dry-run",
        stdout=output,
    )

    payload = json.loads(output.getvalue())
    assert payload["organization_id"] == str(base_data["organization"].id)
    assert payload["dry_run"] is True
    assert payload["result"]["matched"] == 1
    assert not base_data["students"][0].photo


@pytest.mark.django_db
def test_zip_dry_run_supports_registrar_archive(base_data, tmp_path):
    archive_path = tmp_path / "photos.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            f"nested/{base_data['students'][1].national_id}.JPG",
            jpeg_bytes((30, 160, 70)),
        )

    result = StudentPhotoImporter(base_data["organization"]).import_zip(
        archive_path,
        dry_run=True,
    )

    assert result["received"] == 1
    assert result["matched"] == 1
    assert not base_data["students"][1].photo
