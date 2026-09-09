"""Safe student-photo import from the registrar's ``Data/Photo`` assets.

Photo filenames are matched by the student's national identifier.  The
importer is deliberately report-only by default at the service boundary:
callers can preview with ``dry_run=True`` and existing photos are preserved
unless ``overwrite=True`` is explicit.
"""

from __future__ import annotations

import re
from collections import Counter
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

from hamamooz.apps.students.models import Student

MAX_PHOTO_BYTES = 2 * 1024 * 1024


class PhotoImportResult:
    def __init__(self):
        self.received = 0
        self.matched = 0
        self.missing_students = 0
        self.duplicates = 0
        self.duplicate_files = []
        self.skipped_existing = 0
        self.invalid_files = []
        self.orphans = []

    def as_dict(self):
        return {
            "received": self.received,
            "matched": self.matched,
            "missing_students": self.missing_students,
            "duplicates": self.duplicates,
            "duplicate_files": self.duplicate_files,
            "skipped_existing": self.skipped_existing,
            "invalid_files": self.invalid_files,
            "orphans": self.orphans,
        }


_PERSIAN_ARABIC_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_identifier(value):
    """Return only ASCII digits from a registrar filename or identifier."""

    return re.sub(r"\D", "", str(value).strip().translate(_PERSIAN_ARABIC_DIGITS))


def extract_student_identifier(filename):
    """Extract a ten-digit national ID, tolerating copy suffixes and digits.

    Windows exports commonly produce names such as ``0960402306 (2).JPG``.
    The first ten digits are the identity; the suffix is treated as a
    duplicate instead of a different student.  A nine-digit name is accepted
    for the common case where a leading zero was dropped by a spreadsheet.
    Invalid names return ``None`` and are reported rather than queried.
    """

    stem = Path(filename).stem
    normalized = normalize_identifier(stem)
    match = re.search(r"\d{10}", normalized)
    if match:
        return match.group(0)
    if 1 <= len(normalized) <= 9:
        return normalized.zfill(10)
    return None


class StudentPhotoImporter:
    """Import photos scoped to one organization by national ID."""

    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, organization):
        self.organization = organization

    @staticmethod
    def _read_valid_image(source):
        payload = source.read(MAX_PHOTO_BYTES + 1)
        if len(payload) > MAX_PHOTO_BYTES:
            raise ValueError("حجم تصویر نباید بیشتر از ۲ مگابایت باشد.")
        try:
            with Image.open(BytesIO(payload)) as image:
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError("ساختار فایل تصویر معتبر نیست.") from exc
        return payload

    def _save_or_preview(
        self,
        result,
        *,
        filename,
        identifier,
        payload,
        dry_run,
        overwrite,
    ):
        student = Student.objects.filter(
            organization=self.organization,
            national_id=identifier,
        ).first()
        if student is None:
            result.missing_students += 1
            result.orphans.append(filename)
            return
        if student.photo and not overwrite:
            result.skipped_existing += 1
            return
        if not dry_run:
            extension = Path(filename).suffix.lower()
            student.photo.save(
                f"{identifier}{extension}",
                ContentFile(payload),
                save=True,
            )
        result.matched += 1

    def import_zip(self, zip_path, *, dry_run=False, overwrite=False):
        """Preview or import supported photos from a ZIP archive."""

        result = PhotoImportResult()
        try:
            archive_context = ZipFile(zip_path)
        except (BadZipFile, OSError) as exc:
            raise ValueError("فایل ZIP تصاویر معتبر نیست.") from exc

        with archive_context as archive:
            candidates = []
            for item in archive.infolist():
                if item.is_dir():
                    continue
                extension = Path(item.filename).suffix.lower()
                if extension not in self.allowed_extensions:
                    continue
                result.received += 1
                identifier = extract_student_identifier(item.filename)
                if identifier is None:
                    result.invalid_files.append(item.filename)
                    continue
                candidates.append((item.filename, identifier, item))

            duplicate_ids = {
                identifier
                for identifier, count in Counter(
                    identifier for _, identifier, _ in candidates
                ).items()
                if count > 1
            }
            for filename, identifier, _item in candidates:
                if identifier in duplicate_ids:
                    # Never choose an arbitrary portrait when the registrar
                    # supplied more than one image for the same student.
                    result.duplicates += 1
                    result.duplicate_files.append(filename)

            for filename, identifier, item in candidates:
                if identifier in duplicate_ids:
                    continue
                if item.file_size > MAX_PHOTO_BYTES:
                    result.invalid_files.append(item.filename)
                    continue
                try:
                    with archive.open(item) as source:
                        payload = self._read_valid_image(source)
                except (OSError, ValueError) as exc:
                    result.invalid_files.append({"file": item.filename, "reason": str(exc)})
                    continue
                self._save_or_preview(
                    result,
                    filename=filename,
                    identifier=identifier,
                    payload=payload,
                    dry_run=dry_run,
                    overwrite=overwrite,
                )
        return result.as_dict()

    def import_directory(self, directory_path, *, dry_run=False, overwrite=False):
        """Preview or import photos from a mounted ``Data/Photo`` directory."""

        result = PhotoImportResult()
        root = Path(directory_path)
        if not root.is_dir():
            raise ValueError("Photo directory does not exist.")
        root = root.resolve()
        paths = sorted(root.rglob("*"), key=lambda path: str(path))
        candidates = []
        for path in paths:
            if path.is_symlink() or not path.is_file():
                continue
            resolved = path.resolve()
            if not resolved.is_relative_to(root):
                continue
            extension = path.suffix.lower()
            if extension not in self.allowed_extensions:
                continue
            result.received += 1
            display_name = str(path.relative_to(root))
            identifier = extract_student_identifier(path.name)
            if identifier is None:
                result.invalid_files.append(display_name)
                continue
            candidates.append((display_name, identifier, path))

        duplicate_ids = {
            identifier
            for identifier, count in Counter(identifier for _, identifier, _ in candidates).items()
            if count > 1
        }
        for display_name, identifier, _path in candidates:
            if identifier in duplicate_ids:
                # A duplicate is a review queue item, never an implicit
                # "first file wins" decision.
                result.duplicates += 1
                result.duplicate_files.append(display_name)

        for display_name, identifier, path in candidates:
            if identifier in duplicate_ids:
                continue
            try:
                if path.stat().st_size > MAX_PHOTO_BYTES:
                    raise ValueError("حجم تصویر نباید بیشتر از ۲ مگابایت باشد.")
                with path.open("rb") as source:
                    payload = self._read_valid_image(source)
            except (OSError, ValueError) as exc:
                result.invalid_files.append({"file": display_name, "reason": str(exc)})
                continue
            self._save_or_preview(
                result,
                filename=display_name,
                identifier=identifier,
                payload=payload,
                dry_run=dry_run,
                overwrite=overwrite,
            )
        return result.as_dict()
