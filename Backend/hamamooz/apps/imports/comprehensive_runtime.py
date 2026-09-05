import math
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from hamamooz.apps.evaluations.models import MetricScore, MonthlyEvaluation
from hamamooz.apps.organizations.models import AcademicYear, GradeLevel, Term
from hamamooz.apps.students.models import Enrollment

from .comprehensive import EVALUATION_SHEET, GENDER_VALUES, MONTH_NUMBERS
from .comprehensive_flexible import (
    normalize_birth_date,
    normalize_national_id,
    validate_flexible_hardened_comprehensive_workbook,
)
from .comprehensive_hardening import apply_hardened_comprehensive_workbook

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
GRADE_ORDINALS = {
    1: "اول",
    2: "دوم",
    3: "سوم",
    4: "چهارم",
    5: "پنجم",
    6: "ششم",
    7: "هفتم",
    8: "هشتم",
    9: "نهم",
    10: "دهم",
    11: "یازدهم",
    12: "دوازدهم",
}
NON_APPLICABLE_VALUES = {"ندارد", "نامرتبط", "نامربوط", "n/a", "na", "notapplicable"}
TERM_MONTHS = {
    Term.Code.SUMMER: {1, 2, 3},
    Term.Code.FIRST: {4, 5, 6, 7},
    Term.Code.SECOND: {8, 9, 10, 11, 12},
}
TERM_TITLES = {
    Term.Code.SUMMER: "تابستان",
    Term.Code.FIRST: "نوبت اول",
    Term.Code.SECOND: "نوبت دوم",
}
TERM_ORDERS = {Term.Code.SUMMER: 0, Term.Code.FIRST: 1, Term.Code.SECOND: 2}


class ComprehensiveValidationFailed(Exception):
    def __init__(self, *, prepared, errors, profile):
        super().__init__("Comprehensive workbook validation failed.")
        self.prepared = prepared
        self.errors = errors
        self.profile = profile


def _text(value) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip().translate(PERSIAN_DIGITS)


def _label(value) -> str:
    return "".join(
        _text(value)
        .replace("ي", "ی")
        .replace("ك", "ک")
        .replace("‌", " ")
        .replace("ـ", "")
        .split()
    ).lower()


def _json_scalar(value):
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _jalali_to_gregorian(jy, jm, jd):
    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
    days += (jm - 1) * 31 if jm < 7 else ((jm - 7) * 30) + 186
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = gy % 4 == 0 and (gy % 100 != 0 or gy % 400 == 0)
    month_days = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while gm <= 12 and gd > month_days[gm]:
        gd -= month_days[gm]
        gm += 1
    return date(gy, gm, gd)


def _academic_year_parts(raw_code):
    years = re.findall(r"1[34]\d{2}", _text(raw_code))
    if len(years) < 2:
        raise ValueError(
            f'سال تحصیلی "{_text(raw_code)}" قابل تشخیص نیست؛ قالبی مانند 1405-1406 لازم است.'
        )
    start_year, end_year = map(int, years[:2])
    if end_year != start_year + 1:
        raise ValueError("سال تحصیلی فایل باید دو سال شمسی پیاپی داشته باشد.")
    return start_year, end_year


def _grade_order(raw_value):
    normalized = _label(raw_value).replace("پایه", "")
    if normalized.isdigit():
        value = int(normalized)
        return value if 1 <= value <= 12 else None
    for order, title in GRADE_ORDINALS.items():
        if _label(title) == normalized:
            return order
    return None


def _restore(instance):
    fields = []
    if instance.is_deleted:
        instance.is_deleted = False
        instance.deleted_at = None
        fields.extend(["is_deleted", "deleted_at"])
    return fields


def _term_bounds(code, start_year, end_year):
    if code == Term.Code.SUMMER:
        return _jalali_to_gregorian(start_year, 4, 1), _jalali_to_gregorian(start_year, 6, 31)
    if code == Term.Code.FIRST:
        return _jalali_to_gregorian(start_year, 7, 1), _jalali_to_gregorian(start_year, 10, 30)
    return _jalali_to_gregorian(start_year, 11, 1), _jalali_to_gregorian(end_year, 3, 31)


def _detected_term_codes(rows):
    months = set()
    for row in rows:
        if row.get("record_type") != "evaluation":
            continue
        month_no = MONTH_NUMBERS.get(_text(row.get("month")))
        if month_no is None:
            try:
                month_no = int(_text(row.get("month")))
            except (TypeError, ValueError):
                continue
        if 1 <= month_no <= 12:
            months.add(month_no)
    return [code for code, values in TERM_MONTHS.items() if months & values]


def ensure_reference_data_from_workbook(job, rows):
    """Create academic year, grades and only the terms actually present in the workbook."""
    class_rows = [row for row in rows if row.get("record_type") == "class"]
    year_codes = list(
        dict.fromkeys(
            _text(row.get("academic_year_code"))
            for row in class_rows
            if _text(row.get("academic_year_code"))
        )
    )
    if len(year_codes) != 1:
        raise ValueError("فایل باید دقیقاً یک سال تحصیلی مشخص در شیت کلاس‌بندی داشته باشد.")

    year_code = year_codes[0]
    start_jy, end_jy = _academic_year_parts(year_code)
    cycle_start = _jalali_to_gregorian(start_jy, 4, 1)
    cycle_end = _jalali_to_gregorian(end_jy, 3, 31)
    summary = {
        "academic_year_created": 0,
        "academic_year_updated": 0,
        "grades_created": 0,
        "grades_restored": 0,
        "terms_created": 0,
        "terms_updated": 0,
        "detected_term_codes": [],
    }

    academic_year = AcademicYear.all_objects.filter(
        organization=job.organization, code=year_code
    ).first()
    if academic_year is None:
        academic_year = AcademicYear.objects.create(
            organization=job.organization,
            code=year_code,
            title=year_code,
            starts_on=cycle_start,
            ends_on=cycle_end,
            is_current=False,
            is_active=True,
        )
        summary["academic_year_created"] = 1
    else:
        fields = _restore(academic_year)
        desired_start = min(academic_year.starts_on, cycle_start)
        desired_end = max(academic_year.ends_on, cycle_end)
        if academic_year.starts_on != desired_start:
            academic_year.starts_on = desired_start
            fields.append("starts_on")
        if academic_year.ends_on != desired_end:
            academic_year.ends_on = desired_end
            fields.append("ends_on")
        if fields:
            academic_year.full_clean(exclude=["id"])
            academic_year.save(update_fields=[*dict.fromkeys(fields), "updated_at"])
            summary["academic_year_updated"] = 1

    grade_values = list(
        dict.fromkeys(_text(row.get("grade")) for row in class_rows if _text(row.get("grade")))
    )
    for grade_value in grade_values:
        order = _grade_order(grade_value)
        if order is None:
            raise ValueError(f'پایه "{grade_value}" از روی فایل قابل تشخیص نیست.')
        grade = GradeLevel.all_objects.filter(organization=job.organization, order=order).first()
        if grade is None:
            grade = GradeLevel(
                organization=job.organization,
                code=f"grade-{order}",
                title=grade_value,
                order=order,
                is_active=True,
            )
            grade.full_clean(exclude=["id"])
            grade.save()
            summary["grades_created"] += 1
        else:
            fields = _restore(grade)
            if fields:
                grade.save(update_fields=[*fields, "updated_at"])
                summary["grades_restored"] += 1

    detected = _detected_term_codes(rows)
    summary["detected_term_codes"] = list(detected)
    for code in detected:
        starts_on, ends_on = _term_bounds(code, start_jy, end_jy)
        term = Term.all_objects.filter(academic_year=academic_year, code=code).first()
        if term is None:
            term = Term(
                academic_year=academic_year,
                code=code,
                title=TERM_TITLES[code],
                starts_on=starts_on,
                ends_on=ends_on,
                order=TERM_ORDERS[code],
                is_active=True,
            )
            term.full_clean(exclude=["id"])
            term.save()
            summary["terms_created"] += 1
            continue
        fields = _restore(term)
        desired = {
            "title": TERM_TITLES[code],
            "starts_on": starts_on,
            "ends_on": ends_on,
            "order": TERM_ORDERS[code],
            "is_active": True,
        }
        for field, value in desired.items():
            if getattr(term, field) != value:
                setattr(term, field, value)
                fields.append(field)
        if fields:
            term.full_clean(exclude=["id"])
            term.save(update_fields=[*dict.fromkeys(fields), "updated_at"])
            summary["terms_updated"] += 1
    return academic_year, summary


def _canonical_metric(value):
    raw = _text(value)
    if not raw:
        return None, "empty"
    if _label(raw) in NON_APPLICABLE_VALUES:
        return None, "not_applicable"
    try:
        decimal = Decimal(raw)
    except (InvalidOperation, TypeError, ValueError):
        return None, "raw_only"
    integer = int(decimal)
    if decimal == integer and 0 <= integer <= 5:
        return integer, "canonical"
    return None, "raw_only"


def _sanitize_students(rows):
    """Quarantine incomplete student identity rows while preserving the original Import file."""
    class_codes = {
        _text(row.get("class_code"))
        for row in rows
        if row.get("record_type") == "class" and _text(row.get("class_code"))
    }
    seen_local, seen_national, excluded = set(), set(), set()
    quarantined, warnings = [], []
    valid_student_rows = []

    for row in rows:
        if row.get("record_type") != "student":
            continue
        reasons = []
        local_code = _text(row.get("local_code"))
        if not local_code or local_code in seen_local:
            reasons.append("کد محلی خالی یا تکراری است.")
        try:
            national_id, _ = normalize_national_id(row.get("national_id"))
        except ValueError as exc:
            national_id = ""
            reasons.append(str(exc))
        else:
            if national_id in seen_national:
                reasons.append("کد ملی پس از استانداردسازی تکراری است.")
        if not _text(row.get("first_name")) or not _text(row.get("last_name")):
            reasons.append("نام یا نام خانوادگی خالی است.")
        if GENDER_VALUES.get(_text(row.get("gender")).lower()) is None:
            reasons.append("جنسیت معتبر نیست.")
        try:
            normalize_birth_date(row.get("birth_date"))
        except ValueError as exc:
            reasons.append(str(exc))
        if _text(row.get("class_code")) not in class_codes:
            reasons.append("کد کلاس معتبر در شیت کلاس‌بندی پیدا نشد.")

        if reasons:
            if local_code:
                excluded.add(local_code)
            quarantined.append(
                {
                    "sheet": "دانش‌آموزان",
                    "row": row.get("__source_row__"),
                    "local_code": local_code,
                    "national_id": _text(row.get("national_id")),
                    "student_number": _text(row.get("student_number")),
                    "name": f"{_text(row.get('first_name'))} {_text(row.get('last_name'))}".strip(),
                    "reasons": reasons,
                }
            )
            warnings.append(
                {
                    "sheet": "دانش‌آموزان",
                    "row": row.get("__source_row__"),
                    "column": None,
                    "code": "student_row_quarantined",
                    "message": "ردیف ناقص دانش‌آموز وارد داده عملیاتی نشد و جزئیات آن در سابقه Import حفظ شد.",
                    "original": "; ".join(reasons),
                }
            )
            continue
        seen_local.add(local_code)
        seen_national.add(national_id)
        valid_student_rows.append(row)

    valid_ids = {_text(row.get("local_code")) for row in valid_student_rows}
    output = []
    for row in rows:
        if row.get("record_type") == "student":
            if _text(row.get("local_code")) in valid_ids:
                output.append(dict(row))
            continue
        if row.get("record_type") == "evaluation" and _text(row.get("local_code")) in excluded:
            warnings.append(
                {
                    "sheet": EVALUATION_SHEET,
                    "row": row.get("__source_row__"),
                    "column": "کد محلی",
                    "code": "evaluation_row_quarantined",
                    "message": "ارزیابی دانش‌آموز ناقص تا زمان اصلاح هویت وارد مدل عملیاتی نشد.",
                    "original": _text(row.get("local_code")),
                }
            )
            continue
        output.append(dict(row))
    return output, warnings, quarantined


def validate_template_aware_comprehensive_workbook(job, rows):
    safe_rows, warnings, quarantined = _sanitize_students(rows)
    sanitized, payloads = [], {}
    for row in safe_rows:
        cloned = dict(row)
        if row.get("record_type") != "evaluation":
            sanitized.append(cloned)
            continue
        raw_metrics = {
            code: _json_scalar(value) for code, value in (row.get("metrics") or {}).items()
        }
        canonical_metrics = {}
        for metric_code, value in (row.get("metrics") or {}).items():
            canonical, state = _canonical_metric(value)
            if state == "canonical":
                canonical_metrics[metric_code] = canonical
            elif state == "not_applicable":
                warnings.append(
                    {
                        "sheet": EVALUATION_SHEET,
                        "row": row.get("__source_row__"),
                        "column": metric_code,
                        "code": "metric_not_applicable",
                        "message": f"مقدار «ندارد» برای {metric_code} حفظ شد و وارد امتیاز تحلیلی ۰ تا ۵ نشد.",
                        "original": _text(value),
                    }
                )
            elif state == "raw_only":
                warnings.append(
                    {
                        "sheet": EVALUATION_SHEET,
                        "row": row.get("__source_row__"),
                        "column": metric_code,
                        "code": "metric_value_preserved_raw",
                        "message": f"مقدار {metric_code} خارج از قرارداد ۰ تا ۵ است؛ بدون تغییر در داده خام ذخیره شد.",
                        "original": _text(value),
                    }
                )
        cloned["metrics"] = canonical_metrics
        payloads[row.get("__source_row__")] = {
            "raw_metric_values": raw_metrics,
            "source_summary": dict(row.get("__source_summary__") or {}),
        }
        sanitized.append(cloned)

    prepared, errors = validate_flexible_hardened_comprehensive_workbook(job, sanitized)
    prepared.setdefault("warnings", []).extend(warnings)
    prepared["quarantined_students"] = quarantined
    for evaluation in prepared.get("evaluations", []):
        payload = payloads.get(evaluation.get("source_row"), {})
        evaluation["raw_metric_values"] = payload.get("raw_metric_values", {})
        evaluation["source_summary"] = payload.get("source_summary", {})
        evaluation["term_code"] = next(
            (
                code
                for code, months in TERM_MONTHS.items()
                if evaluation.get("month_no") in months
            ),
            None,
        )
    return prepared, errors


def apply_template_aware_comprehensive_workbook(job, prepared):
    summary = apply_hardened_comprehensive_workbook(job, prepared)
    students_by_local = {item["local_code"]: item for item in prepared.get("students", [])}
    national_ids = [item["national_id"] for item in students_by_local.values()]
    enrollments = {
        item.student.national_id: item
        for item in Enrollment.objects.select_related("student").filter(
            academic_year=prepared["academic_year"],
            school=job.school,
            student__national_id__in=national_ids,
        )
    }
    evaluations = {
        (item.enrollment.student.national_id, item.month_no, item.framework_version): item
        for item in MonthlyEvaluation.objects.select_related("enrollment__student").filter(
            enrollment__in=enrollments.values(), source_import_job=job
        )
    }
    terms = {item.code: item for item in Term.objects.filter(academic_year=prepared["academic_year"])}

    summary["metric_scores_cleared_to_raw"] = 0
    saved = 0
    for item in prepared.get("evaluations", []):
        student = students_by_local.get(item["local_code"])
        if student is None:
            continue
        evaluation = evaluations.get(
            (student["national_id"], item["month_no"], item["framework_version"])
        )
        if evaluation is None:
            continue
        raw_values = item.get("raw_metric_values", {})
        raw_only_codes = set(raw_values) - set(item.get("metrics", {}))
        if raw_only_codes:
            deleted, _ = MetricScore.objects.filter(
                evaluation=evaluation, metric_code__in=raw_only_codes
            ).delete()
            summary["metric_scores_cleared_to_raw"] += deleted
        evaluation.raw_metric_values = raw_values
        evaluation.source_summary = item.get("source_summary", {})
        evaluation.term = terms.get(item.get("term_code"))
        evaluation.save(
            update_fields=["raw_metric_values", "source_summary", "term", "updated_at"]
        )
        saved += 1

    summary["raw_evaluation_payloads_saved"] = saved
    summary["quarantined_students"] = prepared.get("quarantined_students", [])
    summary["quarantined_student_count"] = len(prepared.get("quarantined_students", []))
    return summary
