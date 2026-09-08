"""Student photo ZIP import service."""

import re
import zipfile
from pathlib import Path

from django.core.files import File

from hamamooz.apps.students.models import Student


class PhotoImportResult:
    def __init__(self):
        self.received = 0
        self.matched = 0
        self.missing_students = 0
        self.duplicates = 0
        self.orphans = []

    def as_dict(self):
        return {
            "received": self.received,
            "matched": self.matched,
            "missing_students": self.missing_students,
            "duplicates": self.duplicates,
            "orphans": self.orphans,
        }


def normalize_identifier(value):
    # Photo folders often come from Persian Windows installations, where
    # national IDs are stored with Arabic/Persian numerals.
    digits = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return re.sub(r"[^0-9A-Za-z_-]", "", str(value).strip().translate(digits))


def extract_student_identifier(filename):
    stem = Path(filename).stem
    normalized = normalize_identifier(stem)
    # Preserve the exact ten-digit key when a camera/exporter appends a copy
    # suffix such as ``(2)`` to an otherwise valid filename.
    match = re.search(r"\d{10}", normalized)
    return match.group(0) if match else normalized


class StudentPhotoImporter:
    """Import student photos from ZIP archives.

    Filename matching priority:
    national_id -> normalized identifier.
    Unknown students are retained as orphan metadata.
    """

    allowed_extensions = {".jpg", ".jpeg", ".png"}

    def __init__(self, organization):
        self.organization = organization

    def import_zip(self, zip_path):
        result = PhotoImportResult()

        with zipfile.ZipFile(zip_path) as archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue

                extension = Path(item.filename).suffix.lower()
                if extension not in self.allowed_extensions:
                    continue

                result.received += 1
                identifier = extract_student_identifier(item.filename)

                student = Student.objects.filter(
                    organization=self.organization,
                    national_id=identifier,
                ).first()

                if not student:
                    result.missing_students += 1
                    result.orphans.append(item.filename)
                    continue

                with archive.open(item) as source:
                    student.photo.save(
                        f"{identifier}{extension}",
                        File(source),
                        save=True,
                    )

                result.matched += 1

        return result.as_dict()

    def import_directory(self, directory_path):
        """Import photos from a mounted ``Data/Photo`` directory.

        This mirrors :meth:`import_zip` so schools can use the folder already
        supplied by their registrar without first creating an archive.
        """
        result = PhotoImportResult()
        seen = set()
        root = Path(directory_path)
        if not root.is_dir():
            raise ValueError("Photo directory does not exist.")

        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in self.allowed_extensions:
                continue
            result.received += 1
            identifier = extract_student_identifier(path.name)
            if identifier in seen:
                result.duplicates += 1
                result.orphans.append(str(path))
                continue
            seen.add(identifier)
            student = Student.objects.filter(
                organization=self.organization,
                national_id=identifier,
            ).first()
            if not student:
                result.missing_students += 1
                result.orphans.append(str(path))
                continue
            with path.open("rb") as source:
                student.photo.save(
                    f"{identifier}{path.suffix.lower()}",
                    File(source),
                    save=True,
                )
            result.matched += 1

        return result.as_dict()
