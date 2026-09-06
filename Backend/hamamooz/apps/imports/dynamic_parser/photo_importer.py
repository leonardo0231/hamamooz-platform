from __future__ import annotations

from pathlib import Path


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


class PhotoImportResult:
    def __init__(self):
        self.received = 0
        self.matched = 0
        self.missing_students = []
        self.invalid_files = []


class PhotoImporter:
    def extract_national_code(self, filename: str) -> str | None:
        path = Path(filename)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return None
        return path.stem.strip()

    def analyze_files(self, filenames: list[str]) -> PhotoImportResult:
        result = PhotoImportResult()
        result.received = len(filenames)
        for filename in filenames:
            if not self.extract_national_code(filename):
                result.invalid_files.append(filename)
        return result
