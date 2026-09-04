import re
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from hamamooz.apps.evaluations.catalog import FRAMEWORK_VERSION, metric_catalog_for
from hamamooz.apps.organizations.models import AcademicYear, GradeLevel
from hamamooz.apps.students.models import Student

from .comprehensive import (
    CLASS_SHEET,
    EVALUATION_SHEET,
    GENDER_VALUES,
    MONTH_NUMBERS,
    STUDENT_SHEET,
)

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


def _warning(sheet, row, column, code, message, *, original=None, normalized=None):
    item = {
        "sheet": sheet,
        "row": row,
        "column": column,
        "code": code,
        "message": message,
    }
    if original not in (None, ""):
        item["original"] = _text(original)
    if normalized not in (None, ""):
        item["normalized"] = _text(normalized)
    return item


def _error(sheet, row, column, code, message):
    return {
        "sheet": sheet,
        "row": row,
        "column": column,
        "code": code,
        "message": message,
    }


def _jalali_to_gregorian(jy, jm, jd):
    """Convert a validated Jalali date to ``datetime.date`` without extra dependencies."""

    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186

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


def _jalali_month_length(year, month):
    if month <= 6:
        return 31
    if month <= 11:
        return 30
    current_new_year = _jalali_to_gregorian(year, 1, 1)
    next_new_year = _jalali_to_gregorian(year + 1, 1, 1)
    return 30 if (next_new_year - current_new_year).days == 366 else 29


def normalize_birth_date(value):
    """Accept native Excel dates, Gregorian ISO dates, and Jalali YYYY/MM/DD strings."""

    if isinstance(value, datetime):
        return value.date(), False
    if isinstance(value, date):
        return value, False

    raw = _text(value)
    parts = [part for part in re.split(r"[-/.]", raw) if part != ""]
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("تاریخ تولد باید به شکل YYYY/MM/DD یا YYYY-MM-DD باشد.")

    year, month, day = map(int, parts)
    if 1200 <= year <= 1600:
        if not 1 <= month <= 12:
            raise ValueError("ماه تاریخ تولد شمسی معتبر نیست.")
        if not 1 <= day <= _jalali_month_length(year, month):
            raise ValueError("روز تاریخ تولد شمسی معتبر نیست.")
        return _jalali_to_gregorian(year, month, day), True

    try:
        return date(year, month, day), False
    except ValueError as exc:
        raise ValueError("تاریخ تولد معتبر نیست.") from exc


def normalize_national_id(value):
    """Accept lost leading zeros and common formatting while storing canonical 10 digits."""

    raw = _text(value)
    digits = "".join(character for character in raw if character.isdigit())
    if not digits:
        raise ValueError("کد ملی خالی است یا رقم معتبر ندارد.")
    if len(digits) > 10:
        raise ValueError("کد ملی نمی‌تواند بیشتر از ۱۰ رقم باشد.")
    normalized = digits.zfill(10)
    return normalized, normalized != raw


def _grade_aliases(grade):
    aliases = {
        _label(grade.code),
        _label(grade.title),
        _label(str(grade.order)),
        _label(f"پایه {grade.order}"),
        _label(f"پایه{grade.order}"),
    }
    ordinal = GRADE_ORDINALS.get(grade.order)
    if ordinal:
        aliases.update({_label(ordinal), _label(f"پایه {ordinal}"), _label(f"پایه{ordinal}")})
    return {alias for alias in aliases if alias}


def _resolve_academic_year(job, class_rows, warnings, errors):
    raw_codes = [_text(row.get("academic_year_code")) for row in class_rows]
    nonempty_codes = [code for code in raw_codes if code]
    distinct_codes = list(dict.fromkeys(nonempty_codes))
    years = list(AcademicYear.objects.filter(organization=job.organization))

    if len(distinct_codes) > 1:
        normalized_codes = {_label(code) for code in distinct_codes}
        matching = [
            year
            for year in years
            if _label(year.code) in normalized_codes or _label(year.title) in normalized_codes
        ]
        if len({year.id for year in matching}) == 1:
            academic_year = matching[0]
        else:
            errors.append(
                _error(
                    CLASS_SHEET,
                    None,
                    "سال تحصیلی",
                    "academic_year",
                    "کلاس‌ها به چند سال تحصیلی متفاوت اشاره می‌کنند.",
                )
            )
            return None
    elif distinct_codes:
        key = _label(distinct_codes[0])
        academic_year = next(
            (year for year in years if key in {_label(year.code), _label(year.title)}), None
        )
    else:
        academic_year = None

    if academic_year is None:
        current = [year for year in years if year.is_current]
        active = [year for year in years if year.is_active]
        fallback = current[0] if len(current) == 1 else active[0] if len(active) == 1 else None
        if fallback is None and len(years) == 1:
            fallback = years[0]
        if fallback is None:
            errors.append(
                _error(
                    CLASS_SHEET,
                    None,
                    "سال تحصیلی",
                    "academic_year",
                    "سال تحصیلی فایل قابل تطبیق با مجموعه نیست و انتخاب یکتایی برای جایگزینی وجود ندارد.",
                )
            )
            return None
        academic_year = fallback
        warnings.append(
            _warning(
                CLASS_SHEET,
                None,
                "سال تحصیلی",
                "academic_year_fallback",
                "سال تحصیلی فایل مستقیماً شناخته نشد؛ سال تحصیلی جاری/یکتای مجموعه استفاده شد.",
                original=distinct_codes[0] if distinct_codes else "",
                normalized=academic_year.code,
            )
        )

    if not academic_year.is_active:
        warnings.append(
            _warning(
                CLASS_SHEET,
                None,
                "سال تحصیلی",
                "academic_year_inactive",
                "سال تحصیلی انتخاب‌شده غیرفعال است، اما Import برای سازگاری فایل ادامه پیدا کرد.",
                normalized=academic_year.code,
            )
        )
    return academic_year


def _resolve_grade(job, value):
    key = _label(value)
    if not key:
        return None
    for grade in GradeLevel.objects.filter(organization=job.organization):
        if key in _grade_aliases(grade):
            return grade
    return None


def _positive_int(value, field, *, maximum=1000):
    try:
        decimal = Decimal(_text(value))
        result = int(decimal)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} باید عدد صحیح باشد.") from exc
    if decimal != result or not 1 <= result <= maximum:
        raise ValueError(f"{field} باید عدد صحیح بین ۱ و {maximum} باشد.")
    return result


def _normalize_student_number(value, *, national_id, local_code, used_numbers, warnings, row):
    raw = _text(value)
    candidate = raw or national_id or local_code
    if not raw:
        warnings.append(
            _warning(
                STUDENT_SHEET,
                row,
                "شماره دانش‌آموزی",
                "student_number_fallback",
                "شماره دانش‌آموزی خالی بود؛ کد ملی/کد محلی به‌عنوان شناسه ثبت‌نام استفاده شد.",
                normalized=candidate,
            )
        )
    if len(candidate) > 50:
        candidate = candidate[:50]
        warnings.append(
            _warning(
                STUDENT_SHEET,
                row,
                "شماره دانش‌آموزی",
                "student_number_truncated",
                "شماره دانش‌آموزی بیش از طول مجاز بود و برای ذخیره کوتاه شد.",
                original=raw,
                normalized=candidate,
            )
        )
    if candidate in used_numbers:
        suffix = f"-{local_code}"
        candidate = f"{candidate[: 50 - len(suffix)]}{suffix}"
        warnings.append(
            _warning(
                STUDENT_SHEET,
                row,
                "شماره دانش‌آموزی",
                "student_number_deduplicated",
                "شماره دانش‌آموزی تکراری بود؛ کد محلی برای یکتا شدن به آن اضافه شد.",
                original=raw,
                normalized=candidate,
            )
        )
    return candidate


def _normalize_metric_score(value, metric_code, row, warnings):
    try:
        decimal = Decimal(_text(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"امتیاز {metric_code} باید عددی باشد.") from exc

    integer = int(decimal)
    if decimal == integer and 0 <= integer <= 5:
        return integer

    # Some operational workbooks contain an occasional 0..20 domain-style
    # value in a 0..5 metric cell. Accept exact quarter-scale values without
    # silently guessing arbitrary scores (e.g. 20 -> 5, 16 -> 4).
    if decimal == integer and 5 < integer <= 20 and integer % 4 == 0:
        normalized = integer // 4
        warnings.append(
            _warning(
                EVALUATION_SHEET,
                row,
                metric_code,
                "metric_score_scaled",
                f"امتیاز {metric_code} از مقیاس ۲۰ به مقیاس ۵ تبدیل شد.",
                original=integer,
                normalized=normalized,
            )
        )
        return normalized

    raise ValueError(f"امتیاز {metric_code} باید عدد صحیح ۰ تا ۵ باشد.")


def validate_flexible_hardened_comprehensive_workbook(job, rows):
    """Validate the comprehensive workbook while normalizing common school Excel conventions.

    The selected school in the UI is authoritative. Workbook school codes are advisory only,
    leading national-id zeros may be restored, Jalali birth dates are accepted, grade labels
    are resolved by aliases/order, and inactive reference data does not block the import.
    """

    warnings = []
    errors = []
    class_rows = [row for row in rows if row.get("record_type") == "class"]
    student_rows = [row for row in rows if row.get("record_type") == "student"]
    evaluation_rows = [row for row in rows if row.get("record_type") == "evaluation"]

    if not job.school.is_active:
        warnings.append(
            _warning(
                CLASS_SHEET,
                None,
                "کد مدرسه",
                "selected_school_inactive",
                "شعبه انتخاب‌شده غیرفعال است، اما Import طبق انتخاب کاربر ادامه پیدا کرد.",
                normalized=job.school.code,
            )
        )

    seen_school_codes = set()
    for row in class_rows:
        original_school_code = _text(row.get("school_code"))
        if original_school_code in seen_school_codes:
            continue
        seen_school_codes.add(original_school_code)
        if original_school_code != job.school.code:
            warnings.append(
                _warning(
                    CLASS_SHEET,
                    row.get("__source_row__"),
                    "کد مدرسه",
                    "school_code_ignored",
                    "کد مدرسه داخل Excel فقط اطلاعاتی است؛ شعبه انتخاب‌شده در سامانه مبنای Import قرار گرفت.",
                    original=original_school_code,
                    normalized=job.school.code,
                )
            )

    academic_year = _resolve_academic_year(job, class_rows, warnings, errors)

    normalized_classes = []
    seen_class_codes = set()
    for row in class_rows:
        source_row = row.get("__source_row__")
        class_code = _text(row.get("class_code"))
        class_title = _text(row.get("class_title")) or class_code
        grade_value = row.get("grade")
        row_has_error = False

        if not class_code:
            errors.append(_error(CLASS_SHEET, source_row, "کد کلاس", "class", "کد کلاس الزامی است."))
            row_has_error = True
        elif class_code in seen_class_codes:
            errors.append(_error(CLASS_SHEET, source_row, "کد کلاس", "class", "کد کلاس تکراری است."))
            row_has_error = True
        else:
            seen_class_codes.add(class_code)

        grade = _resolve_grade(job, grade_value)
        if grade is None:
            errors.append(
                _error(
                    CLASS_SHEET,
                    source_row,
                    "پایه تحصیلی",
                    "grade",
                    f'پایه "{_text(grade_value)}" با هیچ پایه موجود در مجموعه تطبیق داده نشد.',
                )
            )
            row_has_error = True
        elif not grade.is_active:
            warnings.append(
                _warning(
                    CLASS_SHEET,
                    source_row,
                    "پایه تحصیلی",
                    "grade_inactive",
                    "پایه تطبیق‌داده‌شده غیرفعال است، اما Import ادامه پیدا کرد.",
                    original=grade_value,
                    normalized=grade.code,
                )
            )

        try:
            capacity = _positive_int(row.get("capacity"), "ظرفیت")
        except ValueError as exc:
            errors.append(_error(CLASS_SHEET, source_row, "ظرفیت", "capacity", str(exc)))
            row_has_error = True
            capacity = None

        if not row_has_error:
            normalized_classes.append(
                {
                    "code": class_code,
                    "title": class_title,
                    "grade": grade,
                    "capacity": capacity,
                    "source_row": source_row,
                }
            )

    class_map = {item["code"]: item for item in normalized_classes}
    normalized_students = []
    local_codes = set()
    national_ids = set()
    student_numbers = set()

    for row in student_rows:
        source_row = row.get("__source_row__")
        row_errors = []
        local_code = _text(row.get("local_code"))
        if not local_code:
            local_code = str(source_row or len(normalized_students) + 1)
            warnings.append(
                _warning(
                    STUDENT_SHEET,
                    source_row,
                    "کد محلی",
                    "local_code_generated",
                    "کد محلی خالی بود و از شماره ردیف ساخته شد.",
                    normalized=local_code,
                )
            )
        if local_code in local_codes:
            row_errors.append("کد محلی دانش‌آموز تکراری است.")

        try:
            national_id, national_id_changed = normalize_national_id(row.get("national_id"))
        except ValueError as exc:
            row_errors.append(str(exc))
            national_id = ""
        else:
            if national_id_changed:
                warnings.append(
                    _warning(
                        STUDENT_SHEET,
                        source_row,
                        "کد ملی",
                        "national_id_normalized",
                        "کد ملی با صفرهای ابتدایی/قالب استاندارد ۱۰ رقمی ذخیره شد.",
                        original=row.get("national_id"),
                        normalized=national_id,
                    )
                )
            if national_id in national_ids:
                row_errors.append("کد ملی پس از استانداردسازی در فایل تکراری است.")

        first_name = _text(row.get("first_name"))
        last_name = _text(row.get("last_name"))
        if not first_name or not last_name:
            row_errors.append("نام و نام خانوادگی الزامی است.")

        gender = GENDER_VALUES.get(_text(row.get("gender")).lower())
        if gender is None:
            row_errors.append("جنسیت باید دختر یا پسر باشد.")

        class_code = _text(row.get("class_code"))
        if class_code not in class_map:
            row_errors.append("کد کلاس در شیت کلاس‌بندی پیدا نشد یا کلاس قابل استفاده نیست.")

        try:
            birth_date, was_jalali = normalize_birth_date(row.get("birth_date"))
        except ValueError as exc:
            row_errors.append(str(exc))
            birth_date = None
            was_jalali = False
        if was_jalali:
            warnings.append(
                _warning(
                    STUDENT_SHEET,
                    source_row,
                    "تاریخ تولد",
                    "jalali_birth_date_converted",
                    "تاریخ تولد شمسی Excel به تاریخ میلادی قابل ذخیره در دیتابیس تبدیل شد.",
                    original=row.get("birth_date"),
                    normalized=birth_date.isoformat(),
                )
            )

        if row_errors:
            for message in row_errors:
                errors.append(_error(STUDENT_SHEET, source_row, None, "student", message))
            continue

        student_number = _normalize_student_number(
            row.get("student_number"),
            national_id=national_id,
            local_code=local_code,
            used_numbers=student_numbers,
            warnings=warnings,
            row=source_row,
        )
        local_codes.add(local_code)
        national_ids.add(national_id)
        student_numbers.add(student_number)
        normalized_students.append(
            {
                "local_code": local_code,
                "national_id": national_id,
                "student_number": student_number,
                "first_name": first_name,
                "last_name": last_name,
                "gender": gender,
                "birth_date": birth_date,
                "class_code": class_code,
                "source_row": source_row,
            }
        )

    students_by_local_code = {item["local_code"]: item for item in normalized_students}
    normalized_evaluations = []
    evaluation_keys = set()
    framework_versions = {
        _text(row.get("framework_version"))
        for row in evaluation_rows
        if row.get("framework_version")
    }
    if len(framework_versions) > 1:
        errors.append(
            _error(
                EVALUATION_SHEET,
                None,
                None,
                "framework_version",
                "همه ارزیابی‌های فایل باید یک نسخه چارچوب داشته باشند.",
            )
        )
    workbook_framework_version = next(iter(framework_versions), FRAMEWORK_VERSION)

    for row in evaluation_rows:
        source_row = row.get("__source_row__")
        local_code = _text(row.get("local_code"))
        student = students_by_local_code.get(local_code)
        if student is None:
            errors.append(
                _error(
                    EVALUATION_SHEET,
                    source_row,
                    None,
                    "evaluation",
                    "کد محلی دانش‌آموز در شیت دانش‌آموزان پیدا نشد.",
                )
            )
            continue

        evaluation_national_id = _text(row.get("__evaluation_national_id__"))
        if evaluation_national_id:
            try:
                normalized_evaluation_national_id, _changed = normalize_national_id(
                    evaluation_national_id
                )
            except ValueError as exc:
                errors.append(
                    _error(EVALUATION_SHEET, source_row, "کد ملی", "evaluation_identity", str(exc))
                )
            else:
                if normalized_evaluation_national_id != student["national_id"]:
                    errors.append(
                        _error(
                            EVALUATION_SHEET,
                            source_row,
                            "کد ملی",
                            "evaluation_identity_mismatch",
                            "کد ملی ردیف ارزیابی با دانش‌آموز متناظر یکسان نیست.",
                        )
                    )

        evaluation_class_code = _text(row.get("__evaluation_class_code__"))
        if evaluation_class_code and evaluation_class_code != student["class_code"]:
            errors.append(
                _error(
                    EVALUATION_SHEET,
                    source_row,
                    "کد کلاس",
                    "evaluation_class_mismatch",
                    "کد کلاس ردیف ارزیابی با کلاس دانش‌آموز یکسان نیست.",
                )
            )

        evaluation_full_name = _text(row.get("__evaluation_full_name__"))
        student_full_name = f"{student['first_name']} {student['last_name']}".strip()
        if evaluation_full_name and _label(evaluation_full_name) != _label(student_full_name):
            errors.append(
                _error(
                    EVALUATION_SHEET,
                    source_row,
                    "نام و نام خانوادگی",
                    "evaluation_name_mismatch",
                    "نام ردیف ارزیابی با دانش‌آموز متناظر یکسان نیست.",
                )
            )

        month_text = _text(row.get("month"))
        month_no = MONTH_NUMBERS.get(month_text)
        if month_no is None:
            try:
                month_no = _positive_int(month_text, "ماه", maximum=12)
            except ValueError as exc:
                errors.append(_error(EVALUATION_SHEET, source_row, "ماه", "evaluation", str(exc)))
                continue

        key = (local_code, month_no)
        if key in evaluation_keys:
            errors.append(
                _error(
                    EVALUATION_SHEET,
                    source_row,
                    None,
                    "evaluation",
                    "برای این دانش‌آموز و ماه بیش از یک ردیف ارزیابی وجود دارد.",
                )
            )
            continue

        framework_version = _text(row.get("framework_version")) or workbook_framework_version
        catalog = metric_catalog_for(framework_version)
        if not catalog:
            errors.append(
                _error(
                    EVALUATION_SHEET,
                    source_row,
                    None,
                    "framework_version",
                    f"نسخه چارچوب شاخص‌ها {framework_version} پشتیبانی نمی‌شود.",
                )
            )
            continue

        metrics = {}
        metric_failed = False
        for metric_code, value in row.get("metrics", {}).items():
            if metric_code not in catalog:
                errors.append(
                    _error(
                        EVALUATION_SHEET,
                        source_row,
                        metric_code,
                        "evaluation",
                        f"کد شاخص {metric_code} در چارچوب {framework_version} معتبر نیست.",
                    )
                )
                metric_failed = True
                continue
            try:
                metrics[metric_code] = _normalize_metric_score(
                    value, metric_code, source_row, warnings
                )
            except ValueError as exc:
                errors.append(
                    _error(EVALUATION_SHEET, source_row, metric_code, "evaluation", str(exc))
                )
                metric_failed = True
        if metric_failed:
            continue

        note = _text(row.get("note"))
        if len(note) > 5000:
            errors.append(
                _error(
                    EVALUATION_SHEET,
                    source_row,
                    "توضیحات",
                    "evaluation",
                    "طول توضیحات نباید بیشتر از ۵۰۰۰ نویسه باشد.",
                )
            )
            continue

        evaluation_keys.add(key)
        normalized_evaluations.append(
            {
                "local_code": local_code,
                "month_no": month_no,
                "metrics": metrics,
                "note": note,
                "framework_version": framework_version,
                "source_row": source_row,
            }
        )

    if academic_year is not None:
        capacities = {item["code"]: item["capacity"] for item in normalized_classes}
        desired_counts = Counter(item["class_code"] for item in normalized_students)
        for class_code, count in desired_counts.items():
            capacity = capacities.get(class_code)
            if capacity is not None and count > capacity:
                errors.append(
                    _error(
                        CLASS_SHEET,
                        class_map[class_code]["source_row"],
                        "ظرفیت",
                        "capacity",
                        f"تعداد دانش‌آموزان کلاس {class_code} از ظرفیت فایل بیشتر است.",
                    )
                )

    return {
        "academic_year": academic_year,
        "classes": normalized_classes,
        "students": normalized_students,
        "evaluations": normalized_evaluations,
        "framework_version": workbook_framework_version,
        "warnings": warnings,
    }, errors
