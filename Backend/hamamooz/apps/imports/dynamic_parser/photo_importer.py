from __future__ import annotations

from pathlib import Path
import re


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class PhotoImportResult:
    def __init__(self):
        self.received = 0
        self.matched = 0
        self.missing_students = []
        self.invalid_files = []
        self.duplicates = []


class PhotoImporter:
    def extract_national_code(self, filename: str) -> str | None:
        path = Path(filename)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return None
        code = re.sub(r"\D", "", path.stem)
        if not code:
            return None
        return code.zfill(10)

    def analyze_files(self, filenames: list[str], known_codes: set[str] | None = None):
        result = PhotoImportResult()
        known_codes = known_codes or set()
        seen = set()
        result.received = len(filenames)
        for filename in filenames:
            code = self.extract_national_code(filename)
            if not code:
                result.invalid_files.append(filename)
                continue
            if code in seen:
                result.duplicates.append(filename)
                continue
            seen.add(code)
            if code in known_codes:
                result.matched += 1
            else:
                result.missing_students.append(code)
        return result
