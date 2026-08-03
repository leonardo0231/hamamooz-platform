from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils import timezone

from hamamooz.apps.evaluations.catalog import FRAMEWORK_VERSION, METRIC_CATALOG
from hamamooz.apps.evaluations.models import MetricScore, MonthlyEvaluation
from hamamooz.apps.organizations.models import AcademicYear, ClassSection, GradeLevel
from hamamooz.apps.students.models import Enrollment, Student

from .adapters import LoadedImportRows

COMPREHENSIVE_TEMPLATE_VERSION = "1.0"
COMPREHENSIVE_IMPORT_TYPE = "comprehensive_school"
CLASS_SHEET = "کلاس‌بندی"
STUDENT_SHEET = "دانش‌آموزان"
EVALUATION_SHEET = "ثبت اطلاعات"

CLASS_HEADERS = [
    "ردیف",
    "کد مدرسه",
    "سال تحصیلی",
    "کد کلاس",
    "نام کلاس",
    "پایه تحصیلی",
    "ظرفیت",
]
STUDENT_HEADERS = [
    "ردیف",
    "کد محلی",
    "کد ملی",
    "شماره دانش‌آموزی",
    "نام",
    "نام خانوادگی",
    "جنسیت",
    "تاریخ تولد",
    "کد کلاس",
]
EVALUATION_IDENTITY_HEADERS = [
    "ردیف",
    "ماه",
    "کد محلی",
    "کد ملی",
    "نام و نام خانوادگی",
    "کد کلاس",
]
MONTH_NUMBERS = {
    "تیر": 1,
    "مرداد": 2,
    "شهریور": 3,
    "مهر": 4,
    "آبان": 5,
    "آذر": 6,
    "دی": 7,
    "بهمن": 8,
    "اسفند": 9,
    "فروردین": 10,
    "اردیبهشت": 11,
    "خرداد": 12,
}
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
GENDER_VALUES = {
    "دختر": Student.Gender.FEMALE,
    "female": Student.Gender.FEMALE,
    "زن": Student.Gender.FEMALE,
    "پسر": Student.Gender.MALE,
    "male": Student.Gender.MALE,
    "مرد": Student.Gender.MALE,
}


def _text(value) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip().translate(PERSIAN_DIGITS)


def _label(value) -> str:
    return "".join(_text(value).replace("ي", "ی").replace("ك", "ک").replace("‌", " ").split())


def _sheet(workbook, expected_name):
    expected = _label(expected_name)
    matches = [sheet for sheet in workbook.worksheets if _label(sheet.title) == expected]
    if len(matches) != 1:
        raise ValueError(f"شیت «{expected_name}» در فایل پیدا نشد یا بیش از یک‌بار وجود دارد.")
    return matches[0]


def _error(sheet, row, column, code, message):
    return {
        "sheet": sheet,
        "row": row,
        "column": column,
        "code": code,
        "message": message,
    }


def _validate_headers(sheet, expected, *, start_column=1):
    values = next(
        sheet.iter_rows(
            min_row=4,
            max_row=4,
            min_col=start_column,
            max_col=start_column + len(expected) - 1,
            values_only=True,
        )
    )
    actual = [_label(value) for value in values]
    normalized_expected = [_label(value) for value in expected]
    if actual != normalized_expected:
        raise ValueError(
            f"عنوان ستون‌های شیت «{sheet.title}» در ردیف ۴ با قالب رسمی یکسان نیست."
        )


def _metric_columns(sheet):
    result = {}
    expected_codes = list(METRIC_CATALOG)
    headers = next(
        sheet.iter_rows(min_row=4, max_row=4, min_col=7, max_col=80, values_only=True)
    )
    for offset, (expected_code, header_value) in enumerate(
        zip(expected_codes, headers, strict=True), start=7
    ):
        header = _text(header_value)
        code = header.split("|", maxsplit=1)[0].strip().upper()
        if code != expected_code:
            raise ValueError(
                f"کد شاخص ستون {offset} در شیت «{sheet.title}» باید {expected_code} باشد."
            )
        result[offset] = expected_code
    return result


def load_comprehensive_workbook(job, workbook) -> LoadedImportRows:
    classes_sheet = _sheet(workbook, CLASS_SHEET)
    students_sheet = _sheet(workbook, STUDENT_SHEET)
    evaluation_sheet = _sheet(workbook, EVALUATION_SHEET)
    _validate_headers(classes_sheet, CLASS_HEADERS)
    _validate_headers(students_sheet, STUDENT_HEADERS)
    _validate_headers(evaluation_sheet, EVALUATION_IDENTITY_HEADERS)
    metric_columns = _metric_columns(evaluation_sheet)

    rows = []
    for source_row, values in enumerate(
        classes_sheet.iter_rows(min_row=5, max_row=34, min_col=1, max_col=7, values_only=True),
        start=5,
    ):
        if not any(value not in (None, "") for value in values[1:]):
            continue
        rows.append(
            {
                "record_type": "class",
                "school_code": values[1],
                "academic_year_code": values[2],
                "class_code": values[3],
                "class_title": values[4],
                "grade": values[5],
                "capacity": values[6],
                "__sheet__": CLASS_SHEET,
                "__source_row__": source_row,
            }
        )

    for source_row, values in enumerate(
        students_sheet.iter_rows(min_row=5, max_row=104, min_col=1, max_col=9, values_only=True),
        start=5,
    ):
        if not any(value not in (None, "") for value in values[2:]):
            continue
        rows.append(
            {
                "record_type": "student",
                "local_code": values[1],
                "national_id": values[2],
                "student_number": values[3],
                "first_name": values[4],
                "last_name": values[5],
                "gender": values[6],
                "birth_date": values[7],
                "class_code": values[8],
                "__sheet__": STUDENT_SHEET,
                "__source_row__": source_row,
            }
        )

    for source_row, values in enumerate(
        evaluation_sheet.iter_rows(
            min_row=5,
            max_row=1204,
            min_col=1,
            max_col=94,
            values_only=True,
        ),
        start=5,
    ):
        sequence_value = values[0]
        month_value = values[1]
        local_code_value = values[2]
        metrics = {
            code: values[column - 1]
            for column, code in metric_columns.items()
            if values[column - 1] not in (None, "")
        }
        note = values[93]
        if not metrics and note in (None, ""):
            continue
        sequence = _text(sequence_value)
        derived_local_code = ""
        if sequence.isdigit() and int(sequence) > 0:
            derived_local_code = str(((int(sequence) - 1) // 12) + 1)
        local_code = _text(local_code_value) or derived_local_code
        rows.append(
            {
                "record_type": "evaluation",
                "local_code": local_code,
                "month": month_value,
                "metrics": metrics,
                "note": note,
                "__sheet__": EVALUATION_SHEET,
                "__source_row__": source_row,
            }
        )

    if not any(row["record_type"] == "class" for row in rows):
        raise ValueError("حداقل یک کلاس باید در شیت «کلاس‌بندی» ثبت شده باشد.")
    if not any(row["record_type"] == "student" for row in rows):
        raise ValueError("حداقل یک دانش‌آموز باید در شیت «دانش‌آموزان» ثبت شده باشد.")
    return LoadedImportRows(
        rows=rows,
        source_row_count=len(rows),
        adapter="comprehensive-school-v1",
    )


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    normalized = _text(value).replace("/", "-")
    try:
        result = date.fromisoformat(normalized)
    except (TypeError, ValueError) as exc:
        raise ValueError("تاریخ تولد باید میلادی و با قالب YYYY-MM-DD باشد.") from exc
    if result.year < 1900:
        raise ValueError("تاریخ تولد باید میلادی و با قالب YYYY-MM-DD باشد.")
    return result


def _as_positive_int(value, field, *, maximum=1000):
    try:
        decimal = Decimal(_text(value))
        result = int(decimal)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} باید عدد صحیح باشد.") from exc
    if decimal != result or not 1 <= result <= maximum:
        raise ValueError(f"{field} باید عدد صحیح بین ۱ و {maximum} باشد.")
    return result


def _model_error(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{key}: {', '.join(map(str, messages))}"
            for key, messages in exc.message_dict.items()
        )
    return "; ".join(exc.messages)


def validate_comprehensive_workbook(job, rows):
    errors = []
    class_rows = [row for row in rows if row["record_type"] == "class"]
    student_rows = [row for row in rows if row["record_type"] == "student"]
    evaluation_rows = [row for row in rows if row["record_type"] == "evaluation"]

    year_codes = {_text(row["academic_year_code"]) for row in class_rows}
    if "" in year_codes or len(year_codes) != 1:
        errors.append(
            _error(
                CLASS_SHEET,
                None,
                "سال تحصیلی",
                "academic_year",
                "همه کلاس‌ها باید دقیقاً یک سال تحصیلی معتبر و یکسان داشته باشند.",
            )
        )
        academic_year = None
    else:
        academic_year = AcademicYear.objects.filter(
            organization=job.organization,
            code=next(iter(year_codes)),
            is_active=True,
        ).first()
        if academic_year is None:
            errors.append(
                _error(
                    CLASS_SHEET,
                    None,
                    "سال تحصیلی",
                    "academic_year",
                    "سال تحصیلی فایل در سازمان پیدا نشد یا فعال نیست.",
                )
            )

    grade_values = {_text(row["grade"]) for row in class_rows if _text(row["grade"])}
    grades = GradeLevel.objects.filter(organization=job.organization, is_active=True).filter(
        Q(code__in=grade_values) | Q(title__in=grade_values)
    )
    grade_map = {}
    for grade in grades:
        grade_map.setdefault(_label(grade.code), grade)
        grade_map.setdefault(_label(grade.title), grade)

    normalized_classes = []
    seen_class_codes = set()
    for row in class_rows:
        source_row = row["__source_row__"]
        try:
            school_code = _text(row["school_code"])
            class_code = _text(row["class_code"])
            class_title = _text(row["class_title"])
            grade = grade_map.get(_label(row["grade"]))
            if school_code != job.school.code:
                raise ValueError("کد مدرسه با مدرسه انتخاب‌شده در سامانه یکسان نیست.")
            if not class_code or class_code in seen_class_codes:
                raise ValueError("کد کلاس خالی یا تکراری است.")
            if not class_title:
                raise ValueError("نام کلاس الزامی است.")
            if grade is None:
                raise ValueError("پایه تحصیلی در سازمان پیدا نشد یا فعال نیست.")
            capacity = _as_positive_int(row["capacity"], "ظرفیت")
            seen_class_codes.add(class_code)
            normalized_classes.append(
                {
                    "code": class_code,
                    "title": class_title,
                    "grade": grade,
                    "capacity": capacity,
                    "source_row": source_row,
                }
            )
        except ValueError as exc:
            errors.append(_error(CLASS_SHEET, source_row, None, "class", str(exc)))

    class_map = {item["code"]: item for item in normalized_classes}
    normalized_students = []
    local_codes = set()
    national_ids = set()
    student_numbers = set()
    for row in student_rows:
        source_row = row["__source_row__"]
        try:
            local_code = _text(row["local_code"])
            national_id = _text(row["national_id"]).zfill(10)
            student_number = _text(row["student_number"])
            first_name = _text(row["first_name"])
            last_name = _text(row["last_name"])
            gender = GENDER_VALUES.get(_text(row["gender"]).lower())
            class_code = _text(row["class_code"])
            if not local_code or local_code in local_codes:
                raise ValueError("کد محلی دانش‌آموز خالی یا تکراری است.")
            if len(national_id) != 10 or not national_id.isdigit() or national_id in national_ids:
                raise ValueError("کد ملی باید ۱۰ رقم و در فایل یکتا باشد.")
            if not student_number or student_number in student_numbers:
                raise ValueError("شماره دانش‌آموزی خالی یا تکراری است.")
            if not first_name or not last_name:
                raise ValueError("نام و نام خانوادگی الزامی است.")
            if gender is None:
                raise ValueError("جنسیت باید دختر یا پسر باشد.")
            if class_code not in class_map:
                raise ValueError("کد کلاس در شیت کلاس‌بندی پیدا نشد.")
            birth_date = _as_date(row["birth_date"])
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
        except ValueError as exc:
            errors.append(_error(STUDENT_SHEET, source_row, None, "student", str(exc)))

    students_by_local_code = {item["local_code"]: item for item in normalized_students}
    normalized_evaluations = []
    evaluation_keys = set()
    for row in evaluation_rows:
        source_row = row["__source_row__"]
        try:
            local_code = _text(row["local_code"])
            if local_code not in students_by_local_code:
                raise ValueError("کد محلی دانش‌آموز در شیت دانش‌آموزان پیدا نشد.")
            month_text = _text(row["month"])
            month_no = MONTH_NUMBERS.get(month_text)
            if month_no is None:
                month_no = _as_positive_int(month_text, "ماه", maximum=12)
            key = (local_code, month_no)
            if key in evaluation_keys:
                raise ValueError("برای این دانش‌آموز و ماه بیش از یک ردیف ارزیابی وجود دارد.")
            metrics = {}
            for metric_code, value in row["metrics"].items():
                try:
                    decimal = Decimal(_text(value))
                    score = int(decimal)
                except (InvalidOperation, TypeError, ValueError) as exc:
                    raise ValueError(f"امتیاز {metric_code} باید عدد صحیح ۰ تا ۵ باشد.") from exc
                if decimal != score or score not in range(0, 6):
                    raise ValueError(f"امتیاز {metric_code} باید عدد صحیح ۰ تا ۵ باشد.")
                metrics[metric_code] = score
            note = _text(row["note"])
            if len(note) > 5000:
                raise ValueError("طول توضیحات نباید بیشتر از ۵۰۰۰ نویسه باشد.")
            evaluation_keys.add(key)
            normalized_evaluations.append(
                {
                    "local_code": local_code,
                    "month_no": month_no,
                    "metrics": metrics,
                    "note": note,
                    "source_row": source_row,
                }
            )
        except ValueError as exc:
            errors.append(_error(EVALUATION_SHEET, source_row, None, "evaluation", str(exc)))

    if academic_year is not None:
        class_capacities = {item["code"]: item["capacity"] for item in normalized_classes}
        desired_counts = Counter(item["class_code"] for item in normalized_students)
        for code, count in desired_counts.items():
            if count > class_capacities.get(code, 0):
                errors.append(
                    _error(
                        CLASS_SHEET,
                        class_map[code]["source_row"],
                        "ظرفیت",
                        "capacity",
                        f"تعداد دانش‌آموزان کلاس {code} از ظرفیت فایل بیشتر است.",
                    )
                )

    return {
        "academic_year": academic_year,
        "classes": normalized_classes,
        "students": normalized_students,
        "evaluations": normalized_evaluations,
    }, errors


def _restore(instance):
    if instance.is_deleted:
        instance.is_deleted = False
        instance.deleted_at = None


def apply_comprehensive_workbook(job, prepared):
    academic_year = prepared["academic_year"]
    if academic_year is None:
        raise ValueError("سال تحصیلی معتبر برای اجرای Import وجود ندارد.")
    summary = {
        "classes_created": 0,
        "classes_updated": 0,
        "students_created": 0,
        "students_updated": 0,
        "enrollments_created": 0,
        "enrollments_updated": 0,
        "evaluations_created": 0,
        "evaluations_updated": 0,
        "metric_scores_upserted": 0,
        "final_evaluations": 0,
        "provisional_evaluations": 0,
    }

    class_instances = {}
    existing_classes = {
        item.code: item
        for item in ClassSection.all_objects.select_for_update().filter(
            school=job.school,
            academic_year=academic_year,
            code__in=[item["code"] for item in prepared["classes"]],
        )
    }
    for item in prepared["classes"]:
        instance = existing_classes.get(item["code"])
        if instance is None:
            instance = ClassSection(
                school=job.school,
                academic_year=academic_year,
                code=item["code"],
            )
            summary["classes_created"] += 1
        else:
            summary["classes_updated"] += 1
            _restore(instance)
        instance.title = item["title"]
        instance.grade_level = item["grade"]
        instance.capacity = item["capacity"]
        instance.is_active = True
        instance.full_clean(exclude=["id"])
        instance.save()
        class_instances[item["code"]] = instance

    existing_students = {
        item.national_id: item
        for item in Student.all_objects.select_for_update().filter(
            organization=job.organization,
            national_id__in=[item["national_id"] for item in prepared["students"]],
        )
    }
    student_instances = {}
    for item in prepared["students"]:
        instance = existing_students.get(item["national_id"])
        if instance is None:
            instance = Student(organization=job.organization, national_id=item["national_id"])
            summary["students_created"] += 1
        else:
            summary["students_updated"] += 1
            _restore(instance)
        instance.first_name = item["first_name"]
        instance.last_name = item["last_name"]
        instance.birth_date = item["birth_date"]
        instance.gender = item["gender"]
        instance.status = Student.Status.ACTIVE
        instance.full_clean(exclude=["id"])
        instance.save()
        student_instances[item["local_code"]] = instance

    existing_enrollments = {}
    for existing in (
        Enrollment.all_objects.select_for_update()
        .filter(
            student_id__in=[student.id for student in student_instances.values()],
            academic_year=academic_year,
        )
        .order_by("student_id", "-updated_at")
    ):
        existing_enrollments.setdefault(existing.student_id, existing)
    enrollment_instances = {}
    for item in prepared["students"]:
        student = student_instances[item["local_code"]]
        instance = existing_enrollments.get(student.id)
        if instance is None:
            instance = Enrollment(student=student, academic_year=academic_year)
            summary["enrollments_created"] += 1
        else:
            if (
                not instance.is_deleted
                and instance.status == Enrollment.Status.ACTIVE
                and instance.school_id != job.school_id
            ):
                raise ValueError(
                    f"دانش‌آموز {student.full_name} در همین سال تحصیلی "
                    "ثبت‌نام فعال در مدرسه دیگری دارد."
                )
            summary["enrollments_updated"] += 1
            _restore(instance)
        section = class_instances[item["class_code"]]
        instance.school = job.school
        instance.grade_level = section.grade_level
        instance.class_section = section
        instance.student_number = item["student_number"]
        instance.status = Enrollment.Status.ACTIVE
        instance.enrolled_on = academic_year.starts_on
        instance.left_on = None
        instance.full_clean(exclude=["id"])
        instance.save()
        enrollment_instances[item["local_code"]] = instance

    class_ids = [section.id for section in class_instances.values()]
    final_counts = Counter(
        Enrollment.objects.filter(
            class_section_id__in=class_ids,
            academic_year=academic_year,
            status=Enrollment.Status.ACTIVE,
        ).values_list("class_section_id", flat=True)
    )
    for section in class_instances.values():
        if final_counts[section.id] > section.capacity:
            raise ValueError(f"ظرفیت کلاس {section.title} برای ثبت‌نام‌های نهایی کافی نیست.")

    for item in prepared["evaluations"]:
        enrollment = enrollment_instances[item["local_code"]]
        evaluation = (
            MonthlyEvaluation.objects.select_for_update()
            .filter(
                enrollment=enrollment,
                month_no=item["month_no"],
                framework_version=FRAMEWORK_VERSION,
            )
            .first()
        )
        if evaluation is None:
            evaluation = MonthlyEvaluation.objects.create(
                enrollment=enrollment,
                month_no=item["month_no"],
                framework_version=FRAMEWORK_VERSION,
                note=item["note"],
                recorded_by=job.requested_by,
                source_import_job=job,
            )
            summary["evaluations_created"] += 1
        else:
            evaluation.note = item["note"]
            evaluation.recorded_by = job.requested_by
            evaluation.source_import_job = job
            evaluation.save(
                update_fields=["note", "recorded_by", "source_import_job", "updated_at"]
            )
            summary["evaluations_updated"] += 1
        for metric_code, score in item["metrics"].items():
            MetricScore.objects.update_or_create(
                evaluation=evaluation,
                metric_code=metric_code,
                defaults={"value": score},
            )
            summary["metric_scores_upserted"] += 1
        if len(item["metrics"]) == len(METRIC_CATALOG):
            summary["final_evaluations"] += 1
        else:
            summary["provisional_evaluations"] += 1

    summary["completed_at"] = timezone.now().isoformat()
    return summary
