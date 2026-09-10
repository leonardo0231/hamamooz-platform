"""Optional integration boundary for the independent summer subject exam model.

The subject-exam bounded context is intentionally not imported here.  A future
implementation can expose a provider through the ``SUBJECT_EXAM_RESULT_PROVIDER``
Django setting and return rows for one enrollment at a time.  This keeps the
report contract stable while allowing that model/service to live in another
application or branch.

Provider contract::

    def provider(*, enrollment) -> Iterable[Mapping[str, Any]]:
        ...

Each row may use model-oriented names (for example ``subject__title``) or the
canonical names documented by ``SUMMER_SUBJECT_RESULT_FIELDS``.  The adapter
keeps a JSON-safe ``raw`` copy and emits the same independent collection for
the monthly report, official snapshot, and Student 360 academics response.
It never writes data and never merges these rows into official subjects.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.forms.models import model_to_dict
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

SUBJECT_EXAM_RESULT_PROVIDER_SETTING = "SUBJECT_EXAM_RESULT_PROVIDER"
DEFAULT_SUMMER_EXAM_KEY = "summer"
DEFAULT_SUMMER_EXAM_TITLE = "آزمون تابستانه"
MISSING_SUBJECT_TITLE = "درس ثبت نشده"

SUMMER_SUBJECT_RESULT_FIELDS = (
    "id",
    "enrollment_id",
    "exam_key",
    "exam_title",
    "subject_code",
    "subject_title",
    "grade",
    "class_code",
    "question_count",
    "correct_count",
    "wrong_count",
    "blank_count",
    "percent",
    "highest_percent",
    "rank",
    "t_score",
    "overall_rank",
    "score",
    "final_score",
    "source_file",
    "source_row",
    "raw",
)


class SubjectExamResultProvider(Protocol):
    """Callable boundary implemented by the independent subject-exam context."""

    def __call__(self, *, enrollment: Any) -> Iterable[Mapping[str, Any]]: ...


def _configured_provider() -> Any | None:
    configured = getattr(settings, SUBJECT_EXAM_RESULT_PROVIDER_SETTING, None)
    if configured in (None, ""):
        # The repository-data ingestor stores standalone summer rows in the
        # imports bounded context.  Make that durable model the safe default;
        # the setting remains available for deployments that provide another
        # authorized source.  Keep this import lazy to avoid an imports/reports
        # cycle while Django is loading applications.
        from hamamooz.apps.imports.models import SubjectExamResult

        def provider(*, enrollment):
            filters = {
                "school_id": enrollment.school_id,
                "student_id": enrollment.student_id,
                "exam_period": DEFAULT_SUMMER_EXAM_KEY,
            }
            grade_order = getattr(getattr(enrollment, "grade_level", None), "order", None)
            if grade_order is not None:
                filters["grade_order"] = grade_order
            return SubjectExamResult.objects.filter(**filters).order_by(
                "source_file", "source_sheet", "source_row"
            )

        return provider
    if isinstance(configured, str):
        try:
            configured = import_string(configured)
        except (ImportError, AttributeError) as exc:
            raise ImproperlyConfigured(
                f"{SUBJECT_EXAM_RESULT_PROVIDER_SETTING} must point to a callable provider."
            ) from exc
    if isinstance(configured, type):
        configured = configured()
    return configured


def _provider_rows(provider: Any, enrollment: Any) -> Iterable[Any]:
    for_enrollment = getattr(provider, "for_enrollment", None)
    if callable(for_enrollment):
        rows = for_enrollment(enrollment)
    elif callable(provider):
        rows = provider(enrollment=enrollment)
    else:
        raise ImproperlyConfigured(
            f"{SUBJECT_EXAM_RESULT_PROVIDER_SETTING} is not callable and has no "
            "for_enrollment(enrollment) method."
        )
    if rows is None:
        return []
    if isinstance(rows, Mapping):
        return [rows]
    if isinstance(rows, str | bytes):
        raise ImproperlyConfigured("The subject-exam provider must return row mappings.")
    return rows


def _read(value: Any, aliases: tuple[str, ...]) -> Any | None:
    """Read a field from a dict, a Django model, or a nested relation."""

    for alias in aliases:
        current = value
        found = True
        for part in alias.replace("__", ".").split("."):
            if isinstance(current, Mapping):
                if part not in current:
                    found = False
                    break
                current = current[part]
            else:
                try:
                    current = getattr(current, part)
                except AttributeError:
                    found = False
                    break
        if found and current is not None:
            return current
    return None


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    try:
        return model_to_dict(value)
    except (TypeError, AttributeError, ValueError):
        return {"value": value}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_json_safe(item) for item in value]
    primary_key = getattr(value, "pk", None)
    if primary_key is not None:
        return str(primary_key)
    return str(value)


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str | int | float | Decimal):
        return str(value).strip()
    nested = _read(value, ("title", "name", "label", "code", "pk", "id"))
    if nested is not None and nested is not value:
        return _text(nested, default)
    return str(value).strip()


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text or text.casefold() in {"ندارد", "ثبت نشده", "-", "#n/a", "#value!"}:
        return None
    translation = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    text = text.translate(translation).replace("٬", "").replace("،", "").replace("٫", ".")
    if text.count("/") == 1:
        text = text.replace("/", ".")
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    return float(number)


def _integer(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None and number.is_integer() else None


def _raw_row(row: Any) -> Any:
    explicit_raw = _read(row, ("raw", "raw_data", "raw_values", "source_values"))
    if explicit_raw is not None:
        return _json_safe(explicit_raw)
    return _json_safe(_as_mapping(row))


def _row_enrollment_id(row: Any) -> str | None:
    value = _read(row, ("enrollment_id", "enrollment__id", "enrollment.id", "enrollment"))
    if value is None:
        return None
    nested_id = _read(value, ("pk", "id"))
    return _text(nested_id if nested_id is not None else value)


def normalize_summer_subject_result(row: Any, enrollment: Any) -> dict[str, Any]:
    """Map one provider row to the stable JSON contract."""

    return {
        "id": _text(_read(row, ("id", "pk"))) or None,
        "enrollment_id": _row_enrollment_id(row) or str(enrollment.pk),
        "exam_key": _text(_read(row, ("exam_key", "exam_code", "assessment_key", "exam_period")))
        or DEFAULT_SUMMER_EXAM_KEY,
        "exam_title": _text(_read(row, ("exam_title", "exam_name", "assessment_title")))
        or DEFAULT_SUMMER_EXAM_TITLE,
        "subject_code": _text(_read(row, ("subject_code", "subject__code", "subject.code"))),
        "subject_title": _text(
            _read(
                row,
                (
                    "subject_title",
                    "subject_name",
                    "subject__title",
                    "subject.title",
                    "subject",
                    "title",
                ),
            ),
            MISSING_SUBJECT_TITLE,
        ),
        "grade": _text(
            _read(
                row,
                ("grade", "grade_name", "grade_title", "grade_level__title", "grade_level.title"),
            )
        ),
        "class_code": _text(
            _read(
                row,
                ("class_code", "class_name", "class", "class_section__code", "class_section.code"),
            )
        ),
        "question_count": _integer(
            _read(row, ("question_count", "questions", "question_total", "تعداد سوال"))
        ),
        "correct_count": _integer(_read(row, ("correct_count", "correct", "right_count", "right"))),
        "wrong_count": _integer(_read(row, ("wrong_count", "wrong", "wrong_answers"))),
        "blank_count": _integer(_read(row, ("blank_count", "blank", "unanswered"))),
        "percent": _number(_read(row, ("percent", "percentage", "percent_score"))),
        "highest_percent": _number(
            _read(
                row,
                ("highest_percent", "highest_percentage", "max_percent", "best_percent"),
            )
        ),
        "rank": _integer(_read(row, ("rank", "subject_rank"))),
        "t_score": _number(_read(row, ("t_score", "t_score_value", "standard_score"))),
        "overall_rank": _integer(_read(row, ("overall_rank", "total_rank", "rank_total"))),
        "score": _number(_read(row, ("score", "exam_score", "grade"))),
        "final_score": _number(
            _read(row, ("final_score", "final", "final_grade", "final_score_value"))
        ),
        "source_file": _text(_read(row, ("source_file", "source", "file_name"))),
        "source_row": _integer(_read(row, ("source_row", "row_number", "excel_row"))),
        "raw": _raw_row(row),
    }


def summer_subject_results_for_enrollment(enrollment) -> list[dict[str, Any]]:
    """Return independent summer exam rows for one authorized enrollment.

    A provider must already scope its query to ``enrollment``.  The additional
    enrollment-id check below prevents an accidentally broad provider from
    leaking another enrollment into a report.
    """

    provider = _configured_provider()
    if provider is None:
        return []

    rows = []
    for row in _provider_rows(provider, enrollment):
        row_enrollment_id = _row_enrollment_id(row)
        if row_enrollment_id is not None and row_enrollment_id != str(enrollment.pk):
            logger.warning(
                "subject_exam_result_skipped_for_enrollment",
                extra={
                    "requested_enrollment_id": str(enrollment.pk),
                    "row_enrollment_id": row_enrollment_id,
                },
            )
            continue
        rows.append(normalize_summer_subject_result(row, enrollment))
    return rows


__all__ = [
    "DEFAULT_SUMMER_EXAM_KEY",
    "DEFAULT_SUMMER_EXAM_TITLE",
    "MISSING_SUBJECT_TITLE",
    "SUBJECT_EXAM_RESULT_PROVIDER_SETTING",
    "SUMMER_SUBJECT_RESULT_FIELDS",
    "SubjectExamResultProvider",
    "normalize_summer_subject_result",
    "summer_subject_results_for_enrollment",
]
