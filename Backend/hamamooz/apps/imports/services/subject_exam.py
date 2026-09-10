"""Parser and row-wise ingestor for the three standalone summer exam workbooks.

The comprehensive-school importer intentionally does not know about these files.
This module discovers only the three exact subject-exam filenames, keeps the raw
cells (including formulas), and writes one :class:`SubjectExamResult` per non-empty
worksheet row.  A malformed row changes that row's status; it never rolls back rows
that were already persisted from the same workbook or from another workbook.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from itertools import zip_longest
from pathlib import Path
from typing import Any

from django.db import DatabaseError, transaction
from django.utils import timezone
from openpyxl import load_workbook

from hamamooz.apps.students.models import Student

from ..models import DataSourceManifest, SubjectExamResult


@dataclass(frozen=True)
class SubjectExamWorkbookSpec:
    filename: str
    grade_order: int
    grade_name: str


SUBJECT_EXAM_WORKBOOK_SPECS = (
    SubjectExamWorkbookSpec(
        filename="کارنامه تفصیلی آزمون تابستانه نهم.xlsx",
        grade_order=9,
        grade_name="نهم",
    ),
    SubjectExamWorkbookSpec(
        filename="کارنامه تفصیلی آزمون تابستانه هشتم.xlsx",
        grade_order=8,
        grade_name="هشتم",
    ),
    SubjectExamWorkbookSpec(
        filename="کارنامه تفصیلی آزمون تابستانه هفتم.xlsx",
        grade_order=7,
        grade_name="هفتم",
    ),
)
SUBJECT_EXAM_FILENAMES = tuple(spec.filename for spec in SUBJECT_EXAM_WORKBOOK_SPECS)
_SPECS_BY_FILENAME = {spec.filename: spec for spec in SUBJECT_EXAM_WORKBOOK_SPECS}

_FIELD_ALIASES = {
    "first_name": ("نام",),
    "last_name": ("نام خانوادگی", "نام خانوادگي"),
    "national_id_raw": ("نام کاربری", "کد ملی", "کدملی"),
    "grade_name": ("پایه", "پايه"),
    "class_name": ("کلاس", "نام کلاس", "نام كلاس"),
    "subject_name": ("درس",),
    "question_count": ("تعداد سوال", "تعداد سؤال"),
    "correct_count": ("صحیح",),
    "wrong_count": ("غلط",),
    "blank_count": ("سفید",),
    "percentage": ("درصد",),
    "highest_percentage": ("بالاترین درصد",),
    "rank": ("رتبه",),
    "t_score": ("تراز",),
    "overall_rank": ("رتبه کل",),
    "score": ("نمره",),
    "final_score": ("نمره نهائی", "نمره نهایی"),
}
# The seventh-grade export contains an explicit ``پایه`` column, while the
# eighth- and ninth-grade exports encode the grade in the filename.  The grade
# is therefore optional at header level and is filled from the workbook spec.
_REQUIRED_FIELDS = tuple(field for field in _FIELD_ALIASES if field != "grade_name")
_COUNT_FIELDS = {"question_count", "correct_count", "wrong_count", "blank_count"}
_INTEGER_FIELDS = _COUNT_FIELDS | {"rank", "overall_rank"}
_DECIMAL_FIELDS = {
    "percentage",
    "highest_percentage",
    "t_score",
    "score",
    "final_score",
}
_DECIMAL_RANGES = {
    "percentage": (Decimal("0"), Decimal("100")),
    "highest_percentage": (Decimal("0"), Decimal("100")),
    "t_score": (Decimal("0"), None),
    "score": (Decimal("0"), Decimal("20")),
    "final_score": (Decimal("0"), Decimal("20")),
}
_GRADE_ALIASES = {
    "هفتم": 7,
    "هشتم": 8,
    "نهم": 9,
}
_DIGIT_TRANSLATION = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_FORMULA_PREFIX = "="


@dataclass(frozen=True)
class SubjectExamRow:
    """Parsed representation of one non-empty worksheet row."""

    sheet_name: str
    source_row: int
    raw_values: dict[str, Any]
    raw_fields: dict[str, Any]
    evaluated_values: dict[str, Any]
    evaluated_fields: dict[str, Any]
    missing_headers: tuple[str, ...]


@dataclass(frozen=True)
class ParsedSubjectExamWorkbook:
    spec: SubjectExamWorkbookSpec
    rows: tuple[SubjectExamRow, ...]


def _canonical(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    return re.sub(r"\s+", " ", text).strip().lower()


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _digits(value: Any) -> str:
    return _text(value).translate(_DIGIT_TRANSLATION).replace(" ", "")


def _header_keys(headers: list[Any]) -> list[str]:
    counts: dict[str, int] = {}
    keys: list[str] = []
    for index, header in enumerate(headers, start=1):
        base = _text(header) or f"column_{index}"
        counts[base] = counts.get(base, 0) + 1
        keys.append(base if counts[base] == 1 else f"{base}#{counts[base]}")
    return keys


def _header_map(headers: list[Any]) -> dict[str, int]:
    aliases = {
        field: {_canonical(alias) for alias in values} for field, values in _FIELD_ALIASES.items()
    }
    result: dict[str, int] = {}
    for index, header in enumerate(headers):
        canonical = _canonical(header)
        for field, field_aliases in aliases.items():
            if canonical in field_aliases and field not in result:
                result[field] = index
    return result


def _row_values(headers: list[Any], values: tuple[Any, ...]) -> dict[str, Any]:
    keys = _header_keys(headers)
    mapped = {
        key: _json_value(values[index] if index < len(values) else None)
        for index, key in enumerate(keys)
    }
    # Keep the positional representation as well: it preserves blank cells and
    # protects against duplicate or blank source headers.
    mapped["__headers__"] = [_json_value(value) for value in headers]
    mapped["__values__"] = [_json_value(value) for value in values]
    return mapped


def _field_values(
    headers: list[Any], values: tuple[Any, ...], columns: dict[str, int]
) -> dict[str, Any]:
    return {
        field: _json_value(values[index] if index < len(values) else None)
        for field, index in columns.items()
    }


def _has_value(row: tuple[Any, ...] | None) -> bool:
    return bool(row) and any(value is not None and _text(value) for value in row)


def subject_exam_workbook_spec(path: str | Path) -> SubjectExamWorkbookSpec:
    """Return the spec for an exact standalone subject-exam filename."""

    filename = Path(path).name
    try:
        return _SPECS_BY_FILENAME[filename]
    except KeyError as exc:
        raise ValueError(f"فایل subject exam پشتیبانی نمی‌شود: {filename}") from exc


def discover_subject_exam_workbooks(directory: str | Path) -> list[Path]:
    """Discover only the three configured workbooks below ``directory``.

    Comprehensive workbooks and unrelated Excel files are intentionally ignored.
    Missing files are reported by the public ingestor rather than preventing the
    available workbooks from being processed.
    """

    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"پوشه آزمون درسی پیدا نشد: {root}")
    return [root / filename for filename in SUBJECT_EXAM_FILENAMES if (root / filename).is_file()]


class SubjectExamWorkbookParser:
    """Parse standalone exam workbooks while retaining formula and cached values."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self.spec = subject_exam_workbook_spec(self.path)

    def parse(self) -> ParsedSubjectExamWorkbook:
        raw_workbook = load_workbook(self.path, read_only=True, data_only=False)
        evaluated_workbook = load_workbook(self.path, read_only=True, data_only=True)
        rows: list[SubjectExamRow] = []
        try:
            for raw_sheet in raw_workbook.worksheets:
                evaluated_sheet = evaluated_workbook[raw_sheet.title]
                raw_iterator = raw_sheet.iter_rows(values_only=True)
                evaluated_iterator = evaluated_sheet.iter_rows(values_only=True)
                headers: list[Any] | None = None
                columns: dict[str, int] = {}
                missing_headers: tuple[str, ...] = ()
                for source_row, (raw_row, evaluated_row) in enumerate(
                    zip_longest(raw_iterator, evaluated_iterator, fillvalue=()), start=1
                ):
                    raw_row = tuple(raw_row or ())
                    evaluated_row = tuple(evaluated_row or ())
                    if headers is None:
                        if not _has_value(raw_row):
                            continue
                        headers = list(raw_row)
                        columns = _header_map(headers)
                        missing_headers = tuple(
                            field for field in _REQUIRED_FIELDS if field not in columns
                        )
                        continue
                    if not _has_value(raw_row):
                        continue
                    rows.append(
                        SubjectExamRow(
                            sheet_name=raw_sheet.title,
                            source_row=source_row,
                            raw_values=_row_values(headers, raw_row),
                            raw_fields=_field_values(headers, raw_row, columns),
                            evaluated_values=_row_values(headers, evaluated_row),
                            evaluated_fields=_field_values(headers, evaluated_row, columns),
                            missing_headers=missing_headers,
                        )
                    )
        finally:
            raw_workbook.close()
            evaluated_workbook.close()
        return ParsedSubjectExamWorkbook(spec=self.spec, rows=tuple(rows))


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _national_id(value: Any) -> str | None:
    normalized = _digits(value)
    if len(normalized) == 9 and normalized.isdigit():
        normalized = normalized.zfill(10)
    if len(normalized) != 10 or not normalized.isdigit() or normalized == "0000000000":
        return None
    return normalized


def _add_error(
    errors: list[dict[str, Any]], field: str, code: str, message: str, raw_value: Any = None
) -> None:
    error = {"field": field, "code": code, "message": message}
    if raw_value is not None:
        error["raw_value"] = _json_value(raw_value)
    errors.append(error)


def _bounded_text(
    value: Any,
    *,
    field: str,
    max_length: int,
    errors: list[dict[str, Any]],
) -> str:
    text = _text(value)
    if len(text) > max_length:
        _add_error(
            errors,
            field,
            "too_long",
            f"مقدار ستون {field} بیشتر از {max_length} نویسه است.",
            value,
        )
        return text[:max_length]
    return text


def _numeric_source(
    field: str,
    raw_fields: Mapping[str, Any],
    evaluated_fields: Mapping[str, Any],
    errors: list[dict[str, Any]],
) -> Any:
    raw_value = raw_fields.get(field)
    evaluated_value = evaluated_fields.get(field)
    if (
        evaluated_value is None
        and isinstance(raw_value, str)
        and raw_value.startswith(_FORMULA_PREFIX)
    ):
        _add_error(
            errors,
            field,
            "formula_without_cached_value",
            "فرمول سلول مقدار محاسبه‌شده ندارد.",
            raw_value,
        )
        return None
    return evaluated_value if evaluated_value is not None else raw_value


def _decimal_value(
    field: str,
    value: Any,
    errors: list[dict[str, Any]],
    *,
    minimum: Decimal | None = None,
    maximum: Decimal | None = None,
) -> Decimal | None:
    if value is None or not _text(value):
        _add_error(errors, field, "missing_value", f"مقدار ستون {field} خالی است.")
        return None
    if isinstance(value, bool):
        _add_error(errors, field, "invalid_number", f"مقدار ستون {field} عددی نیست.", value)
        return None
    text = _digits(value).replace(",", "").replace("٬", "").replace("٫", ".")
    if text.endswith("%"):
        text = text[:-1].strip()
    try:
        decimal_value = Decimal(text)
    except (InvalidOperation, ValueError):
        _add_error(errors, field, "invalid_number", f"مقدار ستون {field} عددی نیست.", value)
        return None
    if not decimal_value.is_finite():
        _add_error(errors, field, "invalid_number", f"مقدار ستون {field} عدد متناهی نیست.", value)
        return None
    if minimum is not None and decimal_value < minimum:
        _add_error(errors, field, "out_of_range", f"مقدار ستون {field} کمتر از حد مجاز است.", value)
        return None
    if maximum is not None and decimal_value > maximum:
        _add_error(
            errors, field, "out_of_range", f"مقدار ستون {field} بیشتر از حد مجاز است.", value
        )
        return None
    if abs(decimal_value.as_tuple().exponent) > 4:
        _add_error(
            errors,
            field,
            "too_many_decimals",
            f"مقدار ستون {field} بیش از چهار رقم اعشار دارد.",
            value,
        )
        return None
    if len(decimal_value.as_tuple().digits) > 12:
        _add_error(errors, field, "too_large", f"مقدار ستون {field} بیش از ظرفیت مجاز است.", value)
        return None
    return decimal_value


def _integer_value(field: str, value: Any, errors: list[dict[str, Any]]) -> int | None:
    decimal_value = _decimal_value(field, value, errors, minimum=Decimal("0"))
    if decimal_value is None:
        return None
    if decimal_value != decimal_value.to_integral_value():
        _add_error(errors, field, "not_integer", f"مقدار ستون {field} باید عدد صحیح باشد.", value)
        return None
    integer_value = int(decimal_value)
    if integer_value > 2_147_483_647:
        _add_error(errors, field, "too_large", f"مقدار ستون {field} بیش از ظرفیت مجاز است.", value)
        return None
    return integer_value


def _normalise_row(
    payload: SubjectExamRow,
    spec: SubjectExamWorkbookSpec,
    student_by_national_id: Mapping[str, Any],
) -> dict[str, Any]:
    raw = payload.raw_fields
    evaluated = payload.evaluated_fields
    errors: list[dict[str, Any]] = []
    for field in payload.missing_headers:
        _add_error(errors, field, "missing_header", f"ستون {field} در workbook پیدا نشد.")

    first_name = _bounded_text(
        raw.get("first_name"), field="first_name", max_length=100, errors=errors
    )
    last_name = _bounded_text(
        raw.get("last_name"), field="last_name", max_length=100, errors=errors
    )
    class_name = _bounded_text(
        raw.get("class_name"), field="class_name", max_length=150, errors=errors
    )
    subject_name = _bounded_text(
        raw.get("subject_name"), field="subject_name", max_length=150, errors=errors
    )
    for field, value in (
        ("first_name", first_name),
        ("last_name", last_name),
        ("class_name", class_name),
        ("subject_name", subject_name),
    ):
        if not value:
            _add_error(errors, field, "missing_value", f"مقدار ستون {field} خالی است.")

    national_id_raw = _bounded_text(
        raw.get("national_id_raw"), field="national_id_raw", max_length=100, errors=errors
    )
    national_id = _national_id(national_id_raw)
    if national_id is None:
        _add_error(
            errors,
            "national_id_raw",
            "invalid_national_id",
            "شناسه دانش‌آموز باید ۱۰ رقم باشد و کوتاه نشود.",
            raw.get("national_id_raw"),
        )

    source_grade_name = _text(raw.get("grade_name"))
    grade_name = _bounded_text(
        source_grade_name or spec.grade_name,
        field="grade_name",
        max_length=100,
        errors=errors,
    )
    grade_order = _GRADE_ALIASES.get(_canonical(source_grade_name), spec.grade_order)
    if source_grade_name and grade_order != spec.grade_order:
        _add_error(
            errors,
            "grade_name",
            "grade_mismatch",
            "پایه ردیف با پایه workbook یکسان نیست.",
            source_grade_name,
        )

    parsed: dict[str, Any] = {}
    for field in _INTEGER_FIELDS:
        parsed[field] = _integer_value(
            field,
            _numeric_source(field, raw, evaluated, errors),
            errors,
        )
    for field in _DECIMAL_FIELDS:
        minimum, maximum = _DECIMAL_RANGES[field]
        parsed[field] = _decimal_value(
            field,
            _numeric_source(field, raw, evaluated, errors),
            errors,
            minimum=minimum,
            maximum=maximum,
        )

    student = student_by_national_id.get(national_id) if national_id else None
    if not errors and student is None:
        _add_error(
            errors,
            "student",
            "student_not_found",
            "دانش‌آموزی با این شناسه در مجموعه پیدا نشد.",
            national_id or national_id_raw,
        )
    status = (
        SubjectExamResult.Status.INVALID
        if errors and any(error["code"] != "student_not_found" for error in errors)
        else SubjectExamResult.Status.UNMATCHED
        if errors
        else SubjectExamResult.Status.VALID
    )
    normalized_fields = {
        "first_name": first_name,
        "last_name": last_name,
        "national_id": national_id or "",
        "grade_name": grade_name,
        "grade_order": grade_order,
        "class_name": class_name,
        "subject_name": subject_name,
        **{field: _json_value(value) for field, value in parsed.items()},
    }
    normalized_values = {
        "fields": normalized_fields,
        "raw_fields": {field: _json_value(value) for field, value in raw.items()},
        "evaluated_fields": {field: _json_value(value) for field, value in evaluated.items()},
        "workbook_grade_order": spec.grade_order,
    }
    return {
        "first_name": first_name,
        "last_name": last_name,
        "national_id_raw": national_id_raw,
        "national_id": national_id or "",
        "grade_name": grade_name,
        "grade_order": grade_order,
        "class_name": class_name,
        "subject_name": subject_name,
        "student": student,
        **parsed,
        "normalized_values": normalized_values,
        "errors": errors,
        "error_count": len(errors),
        "status": status,
    }


def _manifest_index(
    manifests: Iterable[DataSourceManifest] | Mapping[str, DataSourceManifest] | None,
) -> dict[tuple[str, str], DataSourceManifest]:
    if manifests is None:
        return {}
    candidates = manifests.values() if isinstance(manifests, Mapping) else manifests
    result: dict[tuple[str, str], DataSourceManifest] = {}
    for manifest in candidates:
        source_file = _text(getattr(manifest, "source_file", ""))
        checksum = _text(getattr(manifest, "checksum", ""))
        if source_file and checksum:
            result[(source_file, checksum)] = manifest
    return result


def _empty_file_result(path: Path, checksum: str, spec: SubjectExamWorkbookSpec) -> dict[str, Any]:
    return {
        "source_file": path.name,
        "source_checksum": checksum,
        "grade_order": spec.grade_order,
        "rows_seen": 0,
        "rows_persisted": 0,
        "rows_created": 0,
        "rows_updated": 0,
        "rows_retired": 0,
        "rows_valid": 0,
        "rows_invalid": 0,
        "rows_unmatched": 0,
        "row_write_errors": 0,
        "errors": [],
    }


def ingest_subject_exam_workbooks(
    school,
    directory: str | Path,
    *,
    manifests: Iterable[DataSourceManifest] | Mapping[str, DataSourceManifest] | None = None,
) -> dict[str, Any]:
    """Ingest the three standalone summer subject-exam workbooks row by row.

    Args:
        school: The branch ``Organization`` that owns the source rows.
        directory: Directory containing the ``Data/Excel`` workbooks.
        manifests: Optional iterable or mapping of already-scanned
            ``DataSourceManifest`` objects.  A row is linked only when both its
            relative filename and checksum match a supplied manifest.

    Returns:
        A JSON-serializable summary containing discovered/missing files and per-file
        row counts.  The operation is idempotent for an unchanged file: its source
        path, checksum, sheet, and row number form the upsert key.

    Notes:
        This function deliberately has no outer transaction.  Each row is persisted
        independently, so malformed data and a failure in one row do not discard
        successful rows from either the same or another workbook.
    """

    root = Path(directory).expanduser().resolve()
    paths = discover_subject_exam_workbooks(root)
    discovered_names = {path.name for path in paths}
    missing_files = [
        filename for filename in SUBJECT_EXAM_FILENAMES if filename not in discovered_names
    ]
    organization_id = getattr(school, "organization_id", None) or school.pk
    student_by_national_id = {
        row["national_id"]: row["id"]
        for row in Student.objects.filter(organization_id=organization_id).values(
            "id", "national_id"
        )
    }
    manifest_by_key = _manifest_index(manifests)
    file_results: list[dict[str, Any]] = []
    total = {
        "rows_seen": 0,
        "rows_persisted": 0,
        "rows_created": 0,
        "rows_updated": 0,
        "rows_retired": 0,
        "rows_valid": 0,
        "rows_invalid": 0,
        "rows_unmatched": 0,
        "row_write_errors": 0,
    }

    for path in paths:
        spec = subject_exam_workbook_spec(path)
        checksum = _checksum(path)
        file_result = _empty_file_result(path, checksum, spec)
        file_results.append(file_result)
        try:
            parsed_workbook = SubjectExamWorkbookParser(path).parse()
        except Exception as exc:  # one unreadable workbook must not hide the others
            file_result["errors"].append({"code": "workbook_read_error", "message": str(exc)})
            continue

        # A changed source path gets a new checksum.  Keep the previous rows in
        # ``all_objects`` for audit, but retire them from the live projection so
        # a replacement workbook can never double-count a student/subject row.
        retired_at = timezone.now()
        file_result["rows_retired"] = (
            SubjectExamResult.objects.filter(
                school=school,
                source_file=path.name,
                exam_period="summer",
            )
            .exclude(source_checksum=checksum)
            .update(
                is_deleted=True,
                deleted_at=retired_at,
                updated_at=retired_at,
            )
        )
        total["rows_retired"] += file_result["rows_retired"]

        manifest = manifest_by_key.get((path.name, checksum))
        for payload in parsed_workbook.rows:
            file_result["rows_seen"] += 1
            total["rows_seen"] += 1
            normalized = _normalise_row(payload, spec, student_by_national_id)
            key = {
                "school": school,
                "source_file": path.name,
                "source_checksum": checksum,
                "source_sheet": payload.sheet_name,
                "source_row": payload.source_row,
            }
            defaults = {
                "organization_id": school.organization_id or school.pk,
                "source_manifest": manifest,
                "exam_period": "summer",
                "first_name": normalized["first_name"],
                "last_name": normalized["last_name"],
                "national_id_raw": normalized["national_id_raw"],
                "national_id": normalized["national_id"],
                "grade_name": normalized["grade_name"],
                "grade_order": normalized["grade_order"],
                "class_name": normalized["class_name"],
                "subject_name": normalized["subject_name"],
                "student_id": normalized["student"],
                **{field: normalized[field] for field in _INTEGER_FIELDS | _DECIMAL_FIELDS},
                "raw_values": payload.raw_values,
                "normalized_values": normalized["normalized_values"],
                "errors": normalized["errors"],
                "error_count": normalized["error_count"],
                "status": normalized["status"],
                "is_deleted": False,
                "deleted_at": None,
            }
            try:
                with transaction.atomic():
                    _, created = SubjectExamResult.all_objects.update_or_create(
                        **key,
                        defaults=defaults,
                    )
            except DatabaseError as exc:
                file_result["row_write_errors"] += 1
                total["row_write_errors"] += 1
                if len(file_result["errors"]) < 20:
                    file_result["errors"].append(
                        {
                            "code": "row_write_error",
                            "row": payload.source_row,
                            "message": str(exc),
                        }
                    )
                continue

            file_result["rows_persisted"] += 1
            total["rows_persisted"] += 1
            count_key = "rows_created" if created else "rows_updated"
            file_result[count_key] += 1
            total[count_key] += 1
            status_key = {
                SubjectExamResult.Status.VALID: "rows_valid",
                SubjectExamResult.Status.INVALID: "rows_invalid",
                SubjectExamResult.Status.UNMATCHED: "rows_unmatched",
            }[normalized["status"]]
            file_result[status_key] += 1
            total[status_key] += 1

    return {
        "directory": str(root),
        "expected_files": list(SUBJECT_EXAM_FILENAMES),
        "discovered_files": [path.name for path in paths],
        "missing_files": missing_files,
        "files": file_results,
        **total,
    }


__all__ = [
    "ParsedSubjectExamWorkbook",
    "SUBJECT_EXAM_FILENAMES",
    "SUBJECT_EXAM_WORKBOOK_SPECS",
    "SubjectExamRow",
    "SubjectExamWorkbookParser",
    "discover_subject_exam_workbooks",
    "ingest_subject_exam_workbooks",
    "subject_exam_workbook_spec",
]
