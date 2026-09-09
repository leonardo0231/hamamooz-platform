from collections import defaultdict
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from hamamooz.apps.academics.calculations import (
    calculate_enrollment_term,
    get_policy,
    normalized_score,
    quantize,
    recalculate_class_term,
)
from hamamooz.apps.academics.models import (
    Assessment,
    CourseOffering,
    Score,
    SubjectResult,
    TermResult,
)
from hamamooz.apps.evaluations.catalog import DOMAIN_DEFINITIONS, METRIC_CATALOG, metric_catalog_for
from hamamooz.apps.evaluations.models import AssessmentPeriod, AssessmentRecord, MonthlyEvaluation
from hamamooz.apps.students.models import Enrollment

from .models import ReportArchive, ReportBatch, ReportBatchItem, ReportDraft

ALLOWED_REPORT_BLOCKS = {
    "student_identity",
    "academic_summary",
    "attendance_summary",
    "evaluation_radar",
    "strengths",
    "weaknesses",
    "recommendations",
    "signatures",
}

# The layout is data, but not executable template source.  Keeping the CSS
# values here prevents a manager-provided presentation JSON object from
# influencing @page with arbitrary text.  Legacy keys remain accepted while
# the renderer normalizes every report to the reviewed A3 print profile.
REPORT_PAGE_SIZE_KEY = "a3_landscape"
ALLOWED_REPORT_PAGE_SIZES = {
    "a4_portrait": "A4 portrait",
    "a3_landscape": "A3 landscape",
    "digital_3x2": "420mm 280mm",
}
REPORT_PAGE_SIZE_CSS = ALLOWED_REPORT_PAGE_SIZES[REPORT_PAGE_SIZE_KEY]

MONTH_LABELS = {
    1: "تیر",
    2: "مرداد",
    3: "شهریور",
    4: "مهر",
    5: "آبان",
    6: "آذر",
    7: "دی",
    8: "بهمن",
    9: "اسفند",
    10: "فروردین",
    11: "اردیبهشت",
    12: "خرداد",
}


def normalize_report_page_size(value=None):
    """Return the single supported report page profile.

    Older snapshots and API clients may still carry ``a4_portrait`` or
    ``digital_3x2``.  They are accepted as migration-compatible input, but
    they must never produce a differently sized report after the print format
    was fixed.
    """

    if value in (None, ""):
        return REPORT_PAGE_SIZE_KEY
    if value not in ALLOWED_REPORT_PAGE_SIZES:
        raise ValueError("Unsupported report page size.")
    return REPORT_PAGE_SIZE_KEY


def report_page_size(presentation):
    """Return the safe, fixed CSS @page value for a frozen presentation."""

    if isinstance(presentation, dict) and presentation.get("page_size") not in (
        None,
        "",
    ):
        # Keep validation strict for unknown values even though all known
        # legacy profiles resolve to A3.
        normalize_report_page_size(presentation.get("page_size"))
    return REPORT_PAGE_SIZE_CSS


def _decimal_string(value, decimal_places=2):
    return f"{value:.{decimal_places}f}" if value is not None else None


def _canonical_domain_scores(rows):
    """Normalize an analytics payload to the nine official report domains.

    The evaluator normally already returns all domains.  This boundary helper
    also covers empty/partial historical snapshots so consumers never infer a
    missing analysis from a shifted list index.  ``None`` remains ``None``;
    zero is preserved only when it was explicitly recorded.
    """

    by_code = {
        str(item.get("code")): item
        for item in (rows or [])
        if isinstance(item, dict) and str(item.get("code") or "") in DOMAIN_DEFINITIONS
    }
    return [
        {
            "code": code,
            "title": item.get("title") or item.get("domain_title") or title,
            "weight": item.get("weight", weight),
            "score": item.get("score") if item.get("score") is not None else None,
            "percent": item.get("percent") if item.get("percent") is not None else None,
            "value_unit": item.get("value_unit", "score_20"),
            "has_data": item.get("has_data", item.get("score") is not None),
            "completed_metrics": item.get("completed_metrics", 0),
            "total_metrics": item.get("total_metrics", 0),
        }
        for code, (title, weight) in DOMAIN_DEFINITIONS.items()
        for item in [by_code.get(code, {})]
    ]


def build_student_snapshot(enrollment, term, *, recalculate=True):
    if recalculate:
        if enrollment.status == Enrollment.Status.ACTIVE:
            recalculate_class_term(enrollment.class_section, term)
        else:
            term_result = calculate_enrollment_term(enrollment, term)
            if term_result.class_rank is not None:
                term_result.class_rank = None
                term_result.save(update_fields=["class_rank", "updated_at"])
    policy = get_policy(enrollment)
    term_result = TermResult.objects.get(enrollment=enrollment, term=term)
    offerings = list(
        CourseOffering.objects.filter(
            class_section=enrollment.class_section, term=term, is_active=True
        ).select_related("grade_subject__subject")
    )
    result_map = {
        row.course_offering_id: row
        for row in SubjectResult.objects.filter(
            enrollment=enrollment, course_offering__in=offerings
        )
    }
    category_buckets = defaultdict(lambda: defaultdict(lambda: [Decimal("0"), Decimal("0")]))
    scores = Score.objects.filter(
        enrollment=enrollment,
        assessment__course_offering__in=offerings,
        assessment__status__in=[Assessment.Status.APPROVED, Assessment.Status.LOCKED],
    ).select_related("assessment", "assessment__assessment_type")
    for score in scores:
        value = normalized_score(score, policy)
        if value is None:
            continue
        offering_id = score.assessment.course_offering_id
        category = score.assessment.assessment_type.category
        category_buckets[offering_id][category][0] += value * score.assessment.weight
        category_buckets[offering_id][category][1] += score.assessment.weight

    subjects = []
    for offering in offerings:
        result = result_map.get(offering.id)
        categories = {
            category: quantize(total / weight, policy) if weight else None
            for category, (total, weight) in category_buckets[offering.id].items()
        }
        subjects.append(
            {
                "title": offering.grade_subject.subject.title,
                "coefficient": str(offering.grade_subject.coefficient),
                "continuous": _decimal_string(categories.get("continuous"), policy.decimal_places),
                "midterm": _decimal_string(categories.get("midterm"), policy.decimal_places),
                "final": _decimal_string(categories.get("final"), policy.decimal_places),
                "average": _decimal_string(
                    result.average if result else None, policy.decimal_places
                ),
                # A missing subject result is not the same as a failed subject.
                # Keep the tri-state value so the React report can show
                # «ثبت نشده» instead of inventing a follow-up status.
                "passed": result.passed if result else None,
            }
        )
    school = enrollment.school
    # Prefer the school-specific mark, while retaining the organization mark
    # as a deterministic fallback for schools that have not uploaded a branch
    # logo yet. The URL is frozen into the report snapshot below.
    logo_url = (
        school.logo.url
        if school.logo
        else school.organization.logo.url
        if school.organization.logo
        else ""
    )
    return {
        "organization": {
            "name": school.organization.name,
        },
        "school": {
            "name": school.official_name or school.name,
            "branch": school.name if school.official_name else "",
            "address": school.address,
            "phone": school.phone,
            "manager": school.manager_name,
            "logo_url": logo_url,
        },
        "student": {
            "full_name": enrollment.student.full_name,
            "national_id": enrollment.student.national_id,
            "student_number": enrollment.student_number,
            "photo_url": enrollment.student.photo.url if enrollment.student.photo else "",
        },
        "academic": {
            "year": enrollment.academic_year.title,
            "term": term.title,
            "grade": enrollment.grade_level.title,
            "class": enrollment.class_section.title,
        },
        "subjects": subjects,
        "summary": {
            "average": _decimal_string(term_result.average, policy.decimal_places),
            "class_rank": term_result.class_rank,
            "passed": term_result.passed,
            "status_label": "قبول" if term_result.passed else "نیازمند بررسی",
            "formula_version": term_result.formula_version,
        },
    }


def _json_number(value):
    if value is None:
        return None
    value = Decimal(str(value))
    return int(value) if value == int(value) else float(value)


def _data_path_metric_score(record):
    """Return an analytical 0..20 score only when the unit is authoritative."""

    if record.status != "recorded" or record.score is None:
        return None
    if record.value_kind == "rubric_5":
        return record.score * Decimal("4")
    if record.value_kind == "score_20":
        return record.score
    # Signed deltas and unknown numeric/text values are stored and displayed,
    # but they are not silently mixed into a level/average score.
    return None


def _data_path_metric_row(record, catalog):
    definition = catalog.get(record.indicator.code) or METRIC_CATALOG.get(record.indicator.code, {})
    return {
        "code": record.indicator.code,
        "title": definition.get("title", record.indicator.title),
        "domain_code": definition.get("domain_code", record.indicator.category),
        "domain_title": definition.get(
            "domain_title",
            DOMAIN_DEFINITIONS.get(record.indicator.category, (record.indicator.category, 0))[0],
        ),
        "value": _json_number(record.score),
        "raw_value": record.raw_value,
        "value_kind": record.value_kind,
        "value_unit": record.value_kind,
        "status": record.status,
        "has_data": record.status == "recorded" and record.score is not None,
    }


def _data_path_month_summary(records, catalog):
    rows = [_data_path_metric_row(record, catalog) for record in records]
    grouped = defaultdict(list)
    for record in records:
        score = _data_path_metric_score(record)
        domain_code = record.indicator.category
        if score is not None and domain_code:
            grouped[domain_code].append(score)

    domain_scores = []
    for code, (title, weight) in DOMAIN_DEFINITIONS.items():
        values = grouped.get(code, [])
        total_metrics = sum(
            1
            for definition in catalog.values()
            if definition.get("domain_code") == code
        )
        score = (sum(values) / len(values)).quantize(Decimal("0.01")) if values else None
        domain_scores.append(
            {
                "code": code,
                "title": title,
                "weight": weight,
                "score": _json_number(score),
                "percent": _json_number(score * Decimal("5")) if score is not None else None,
                "value_unit": "score_20",
                "completed_metrics": sum(
                    1 for record in records if record.indicator.category == code
                ),
                "total_metrics": total_metrics,
                "has_data": score is not None,
            }
        )
    scored_domains = [item for item in domain_scores if item["score"] is not None]
    total_weight = sum(item["weight"] for item in scored_domains)
    overall = (
        sum(Decimal(str(item["score"])) * item["weight"] for item in scored_domains)
        / total_weight
        if total_weight
        else None
    )
    total_metrics = len(catalog)
    completed_metrics = sum(1 for record in records if record.status == "recorded")
    completion_percent = round(completed_metrics * 100 / total_metrics, 2) if total_metrics else 0.0
    required_metrics = total_metrics
    return {
        "metrics": rows,
        "metric_scores": {
            row["code"]: row["value"] for row in rows if row["value"] is not None
        },
        "domain_scores": domain_scores,
        "overall_score": _json_number(overall.quantize(Decimal("0.01"))) if overall else None,
        "completed_metrics": completed_metrics,
        "required_metrics": required_metrics,
        "completion_percent": completion_percent,
        "completion_status": "final" if completed_metrics >= required_metrics else "provisional",
        "completion_warning": (
            None
            if completed_metrics >= required_metrics
            else f"اطلاعات ناقص است؛ {completed_metrics} شاخص از {required_metrics} شاخص ثبت شده است."
        ),
    }


def _data_path_extended_context(enrollment, month_no):
    records = list(
        AssessmentRecord.objects.filter(
            student=enrollment.student,
            period__academic_year=enrollment.academic_year,
            period__period_type=AssessmentPeriod.PeriodType.MONTHLY,
            period__order__lte=month_no,
        )
        .select_related("period", "indicator")
        .order_by("period__order", "indicator__code")
    )
    records_by_month = defaultdict(list)
    for record in records:
        records_by_month[record.period.order].append(record)

    # Older manual imports predate AssessmentRecord.  Make them visible in a
    # Data report without changing their canonical legacy storage.
    if not records:
        for evaluation in (
            MonthlyEvaluation.objects.filter(
                enrollment=enrollment,
                month_no__lte=month_no,
            )
            .prefetch_related("metric_scores")
            .order_by("month_no")
        ):
            catalog = metric_catalog_for(evaluation.framework_version) or METRIC_CATALOG
            for metric in evaluation.metric_scores.all():
                definition = catalog.get(metric.metric_code, {})
                records_by_month[evaluation.month_no].append(
                    {
                        "indicator": type(
                            "LegacyIndicator",
                            (),
                            {
                                "code": metric.metric_code,
                                "title": definition.get("title", metric.metric_code),
                                "category": definition.get("domain_code", ""),
                            },
                        )(),
                        "score": Decimal(metric.value),
                        "raw_value": str(metric.value),
                        "value_kind": "rubric_5",
                        "status": "recorded",
                    }
                )

    evaluations = []
    all_catalog = METRIC_CATALOG
    for current_month, month_records in sorted(records_by_month.items()):
        real_records = [record for record in month_records if not isinstance(record, dict)]
        if real_records:
            catalog = all_catalog
            summary = _data_path_month_summary(real_records, catalog)
        else:
            # Convert legacy rows to the same public contract without relying
            # on the dynamic model's fields.
            rows = []
            grouped = defaultdict(list)
            for record in month_records:
                indicator = record["indicator"]
                domain_code = indicator.category
                score = record["score"] * Decimal("4")
                rows.append(
                    {
                        "code": indicator.code,
                        "title": indicator.title,
                        "domain_code": domain_code,
                        "domain_title": DOMAIN_DEFINITIONS.get(domain_code, ("", 0))[0],
                        "value": _json_number(record["score"]),
                        "raw_value": record["raw_value"],
                        "value_kind": "rubric_5",
                        "value_unit": "rubric_5",
                        "status": "recorded",
                        "has_data": True,
                    }
                )
                grouped[domain_code].append(score)
            domains = []
            for code, (title, weight) in DOMAIN_DEFINITIONS.items():
                values = grouped.get(code, [])
                score = sum(values) / len(values) if values else None
                domains.append(
                    {
                        "code": code,
                        "title": title,
                        "weight": weight,
                        "score": _json_number(score),
                        "percent": _json_number(score * Decimal("5")) if score is not None else None,
                        "value_unit": "score_20",
                        "completed_metrics": len(values),
                        "total_metrics": sum(1 for item in METRIC_CATALOG.values() if item["domain_code"] == code),
                        "has_data": score is not None,
                    }
                )
            scored = [item for item in domains if item["score"] is not None]
            total_weight = sum(item["weight"] for item in scored)
            overall = (
                sum(Decimal(str(item["score"])) * item["weight"] for item in scored) / total_weight
                if total_weight
                else None
            )
            summary = {
                "metrics": rows,
                "metric_scores": {row["code"]: row["value"] for row in rows},
                "domain_scores": domains,
                "overall_score": _json_number(overall),
                "completed_metrics": len(rows),
                "required_metrics": len(METRIC_CATALOG),
                "completion_percent": round(len(rows) * 100 / len(METRIC_CATALOG), 2),
                "completion_status": "provisional",
                "completion_warning": "دادهٔ قدیمی فقط برای شاخص‌های ثبت‌شده در دسترس است.",
            }
        evaluations.append(
            {
                "month_no": current_month,
                "month_title": MONTH_LABELS.get(current_month, str(current_month)),
                "framework_version": "data_path",
                **summary,
            }
        )

    latest = next(
        (item for item in evaluations if item["month_no"] == month_no),
        evaluations[-1] if evaluations else None,
    )
    current_domain_scores = latest["domain_scores"] if latest else [
        {
            "code": code,
            "title": title,
            "weight": weight,
            "score": None,
            "percent": None,
            "value_unit": "score_20",
            "completed_metrics": 0,
            "total_metrics": sum(1 for item in METRIC_CATALOG.values() if item["domain_code"] == code),
            "has_data": False,
        }
        for code, (title, weight) in DOMAIN_DEFINITIONS.items()
    ]
    analysis = {
        "completion_status": latest["completion_status"] if latest else "provisional",
        "completion_percent": latest["completion_percent"] if latest else 0.0,
        "overall_score": latest["overall_score"] if latest else None,
        "performance_level": None,
        "first_month": evaluations[0]["month_no"] if evaluations else None,
        "last_month": latest["month_no"] if latest else None,
        "change": None,
        "trend": "insufficient_data",
        "trend_label": "داده ناکافی",
        "recommendation": None,
        "completion_warning": latest["completion_warning"] if latest else "هنوز ارزیابی ماهانه‌ای ثبت نشده است.",
        "rank_scope": "class",
        "rank": None,
        "ranked_count": 0,
        "domain_scores": _canonical_domain_scores(current_domain_scores),
        "monthly_scores": [
            {
                key: value
                for key, value in item.items()
                if key not in {"metrics", "metric_scores"}
            }
            for item in evaluations
        ],
    }
    return {
        "evaluations": evaluations,
        "evaluation_analysis": analysis,
        "latest_evaluation": latest,
        "report_mode": ReportArchive.ReportMode.DATA_MONTHLY,
        "month_no": month_no,
        "attendance": {
            "finalized_session_count": 0,
            "record_count": 0,
            "present_count": 0,
            "unexcused_absence_count": 0,
            "excused_absence_count": 0,
            "late_count": 0,
            "attendance_rate": None,
        },
        "behavior_events": [],
        "activities": [],
        "analytics_signals": [],
        "approved_recommendations": [],
        "support_notes": [],
    }


def build_data_path_student_snapshot(enrollment, month_no):
    school = enrollment.school
    logo_url = (
        school.logo.url
        if school.logo
        else school.organization.logo.url
        if school.organization.logo
        else ""
    )
    return {
        "organization": {"name": school.organization.name},
        "school": {
            "name": school.official_name or school.name,
            "branch": school.name if school.official_name else "",
            "address": school.address,
            "phone": school.phone,
            "manager": school.manager_name,
            "logo_url": logo_url,
        },
        "student": {
            "full_name": enrollment.student.full_name,
            "national_id": enrollment.student.national_id,
            "student_number": enrollment.student_number,
            "photo_url": enrollment.student.photo.url if enrollment.student.photo else "",
        },
        "academic": {
            "year": enrollment.academic_year.title,
            "term": f"ماه {MONTH_LABELS.get(month_no, month_no)}",
            "grade": enrollment.grade_level.title,
            "class": enrollment.class_section.title,
        },
        "subjects": [],
        "summary": {
            "average": None,
            "class_rank": None,
            "passed": None,
            "status_label": "گزارش ماهانه مسیر Data",
            "formula_version": "data_path_monthly_v1",
        },
    }


def build_monthly_analytical_snapshot(enrollment, month_no, *, page_size=REPORT_PAGE_SIZE_KEY):
    snapshot = {"reports": [build_data_path_student_snapshot(enrollment, month_no)]}
    report = snapshot["reports"][0]
    report["product_context"] = _data_path_extended_context(enrollment, month_no)
    report["history"] = []
    snapshot["template"] = {
        "blocks": list(ALLOWED_REPORT_BLOCKS),
        "presentation": {"page_size": normalize_report_page_size(page_size)},
    }
    return snapshot


def build_report_snapshot(report_type, term, enrollment=None, class_section=None):
    if report_type == ReportArchive.ReportType.STUDENT_REPORT_CARD:
        return {"reports": [build_student_snapshot(enrollment, term)]}
    enrollments = list(
        Enrollment.all_objects.filter(
            class_section=class_section,
            enrolled_on__lte=term.ends_on,
            is_deleted=False,
        )
        .filter(Q(left_on__isnull=True) | Q(left_on__gte=term.starts_on))
        .select_related("student", "school", "academic_year", "grade_level", "class_section")
    )
    recalculate_class_term(class_section, term)
    return {
        "reports": [build_student_snapshot(item, term, recalculate=False) for item in enrollments]
    }


def build_analytical_snapshot(enrollment, term, *, page_size=REPORT_PAGE_SIZE_KEY):
    """Frozen snapshot for the coloured student report and its in-app view."""
    snapshot = build_report_snapshot(
        ReportArchive.ReportType.STUDENT_REPORT_CARD, term, enrollment=enrollment
    )
    report = snapshot["reports"][0]
    report["product_context"] = _report_extended_context(enrollment)
    history_rows = (
        TermResult.objects.filter(enrollment__student=enrollment.student)
        .select_related("term", "enrollment__academic_year", "enrollment__grade_level")
        .order_by("-enrollment__academic_year__starts_on", "-term__ends_on")
    )
    # A growth point represents the final available result of one academic
    # year, not two terms of the same year.  This is the promised three-year
    # learning trajectory, even when the current year is still in progress.
    history_by_year = {}
    for item in history_rows:
        history_by_year.setdefault(item.enrollment.academic_year_id, item)
        if len(history_by_year) == 3:
            break
    history = list(history_by_year.values())[:3]
    report["history"] = [
        {
            "label": item.enrollment.grade_level.title,
            "year": item.enrollment.academic_year.title,
            "average": _decimal_string(item.average),
            "rank": item.class_rank,
        }
        for item in reversed(history)
        if item.average is not None
    ]
    snapshot["template"] = {
        "blocks": list(ALLOWED_REPORT_BLOCKS),
        "presentation": {"page_size": normalize_report_page_size(page_size)},
    }
    return snapshot


def build_report_render_snapshot(
    report_type,
    term,
    *,
    enrollment=None,
    class_section=None,
    report_mode=ReportArchive.ReportMode.OFFICIAL_TERM,
    month_no=None,
):
    """Build the presentation snapshot used by preview and archived reports.

    Student report cards have a richer, A3 analytical presentation.  Keeping this
    choice in one place prevents the preview, a single archived report, and a
    batch report from silently using different data contracts.
    """

    if report_mode == ReportArchive.ReportMode.DATA_MONTHLY:
        if month_no is None:
            raise ValueError("گزارش ماهانه مسیر Data به شماره ماه نیاز دارد.")
        if report_type == ReportArchive.ReportType.STUDENT_REPORT_CARD:
            if enrollment is None:
                raise ValueError("Student report cards require an enrollment.")
            return build_monthly_analytical_snapshot(enrollment, month_no)
        enrollments = Enrollment.objects.filter(
            class_section=class_section,
            academic_year=class_section.academic_year,
            status=Enrollment.Status.ACTIVE,
        ).select_related("student", "school", "academic_year", "grade_level", "class_section")
        return {
            "reports": [
                build_monthly_analytical_snapshot(item, month_no)["reports"][0]
                for item in enrollments
            ],
            "template": {
                "blocks": list(ALLOWED_REPORT_BLOCKS),
                "presentation": {"page_size": REPORT_PAGE_SIZE_KEY},
            },
        }
    if report_type == ReportArchive.ReportType.STUDENT_REPORT_CARD:
        if enrollment is None:
            raise ValueError("Student report cards require an enrollment.")
        return build_analytical_snapshot(enrollment, term)
    return build_report_snapshot(report_type, term, class_section=class_section)


def render_report_batch(batch_id):
    """Render every queued item independently, then package successful PDFs."""
    batch = ReportBatch.objects.select_related(
        "organization", "school", "academic_year", "term", "requested_by"
    ).get(pk=batch_id)
    batch.status = ReportBatch.Status.PROCESSING
    batch.started_at = timezone.now()
    batch.save(update_fields=["status", "started_at", "updated_at"])
    output = BytesIO()
    completed = failed = 0
    with ZipFile(output, "w", ZIP_DEFLATED) as archive_zip:
        for item in batch.items.select_related(
            "enrollment__student", "enrollment__class_section"
        ).all():
            item.status = ReportBatchItem.Status.PROCESSING
            item.save(update_fields=["status", "updated_at"])
            try:
                batch_item_enrollment = item.enrollment
                if batch.report_mode == ReportBatch.ReportMode.DATA_MONTHLY:
                    snapshot = build_monthly_analytical_snapshot(
                        batch_item_enrollment, batch.month_no, page_size=batch.page_size
                    )
                else:
                    snapshot = build_analytical_snapshot(
                        batch_item_enrollment, batch.term, page_size=batch.page_size
                    )
                report = ReportArchive.objects.create(
                    organization=batch.organization,
                    school=batch.school,
                    academic_year=batch.academic_year,
                    term=batch.term,
                    report_mode=batch.report_mode,
                    month_no=batch.month_no,
                    report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
                    status=ReportArchive.Status.PROCESSING,
                    enrollment=batch_item_enrollment,
                    requested_by=batch.requested_by,
                    output_format=ReportArchive.OutputFormat.PDF,
                    snapshot=snapshot,
                    started_at=timezone.now(),
                )
                pdf = render_report_pdf(snapshot)
                safe_id = batch_item_enrollment.student.national_id or str(
                    batch_item_enrollment.student_id
                )
                filename = f"{safe_id}-{batch_item_enrollment.student.full_name}.pdf".replace(
                    "/", "-"
                )
                report.output_file.save(filename, ContentFile(pdf), save=False)
                report.status = ReportArchive.Status.COMPLETED
                report.completed_at = timezone.now()
                report.formula_version = snapshot["reports"][0]["summary"]["formula_version"]
                report.save()
                report.output_file.open("rb")
                archive_zip.writestr(filename, report.output_file.read())
                item.report, item.status, item.error_message = (
                    report,
                    ReportBatchItem.Status.COMPLETED,
                    "",
                )
                item.save(update_fields=["report", "status", "error_message", "updated_at"])
                completed += 1
            except Exception as exc:  # one student must never abort a school batch
                item.status, item.error_message = ReportBatchItem.Status.FAILED, str(exc)[:2000]
                item.save(update_fields=["status", "error_message", "updated_at"])
                failed += 1
    batch.completed_count, batch.failed_count = completed, failed
    batch.completed_at = timezone.now()
    batch.status = (
        ReportBatch.Status.COMPLETED
        if failed == 0
        else (ReportBatch.Status.PARTIAL if completed else ReportBatch.Status.FAILED)
    )
    if completed:
        batch.zip_file.save(
            f"report-batch-{batch.id}.zip", ContentFile(output.getvalue()), save=False
        )
    batch.save()
    return batch


def _local_media_file_url(url):
    if not url or not url.startswith(settings.MEDIA_URL):
        return url
    relative = url.removeprefix(settings.MEDIA_URL).lstrip("/")
    media_root = Path(settings.MEDIA_ROOT).resolve()
    candidate = (media_root / relative).resolve()
    if not candidate.is_relative_to(media_root):
        return ""
    if not candidate.is_file():
        # A stale model file must not become a broken image in an archived PDF.
        # The React report entry renders its explicit missing-photo/logo state.
        return ""
    return candidate.as_uri()


def _pdf_snapshot(snapshot):
    rendered = deepcopy(snapshot)
    for report in rendered.get("reports", []):
        report["school"]["logo_url"] = _local_media_file_url(report["school"].get("logo_url", ""))
        report["student"]["photo_url"] = _local_media_file_url(
            report["student"].get("photo_url", "")
        )
    return rendered


def render_report_pdf(snapshot):
    """Render a frozen report snapshot through the Chromium boundary.

    Production always uses the explicitly provisioned Chromium renderer and
    raises a clear error when Playwright or its browser bundle is unavailable;
    callers cannot supply an alternate server-side renderer.
    """

    from .rendering import render_production_report_pdf

    return render_production_report_pdf(snapshot)


def render_report_docx(snapshot):
    """Render a fixed, reviewed DOCX template from a frozen report snapshot.

    The document template is shipped with the application.  Managers configure
    only allowlisted layout blocks; they never upload executable Jinja or Python.
    """
    from docxtpl import DocxTemplate

    template_path = Path(settings.BASE_DIR) / "templates" / "reports" / "report_card.docx"
    if not template_path.is_file():
        raise ValueError("The approved DOCX report template is unavailable.")
    template = snapshot.get("template", {})
    document = DocxTemplate(template_path)
    document.render(
        {
            "reports": snapshot.get("reports", []),
            "blocks": template.get("blocks", ALLOWED_REPORT_BLOCKS),
            "overrides": snapshot.get("content_overrides", {}),
            "generated_at": timezone.now(),
        }
    )
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def _report_extended_context(enrollment):
    """Build a no-counseling snapshot extension from approved, scoped domains."""
    from hamamooz.apps.activities.models import ActivityParticipation
    from hamamooz.apps.analytics.models import StudentRiskSignal
    from hamamooz.apps.attendance.models import AttendanceRecord, AttendanceSession
    from hamamooz.apps.behavior.models import BehaviorEvent
    from hamamooz.apps.evaluations.catalog import METRIC_CATALOG, metric_catalog_for
    from hamamooz.apps.evaluations.models import MonthlyEvaluation
    from hamamooz.apps.evaluations.services import EvaluationAnalyticsService
    from hamamooz.apps.recommendations.models import Recommendation

    attendance_records = AttendanceRecord.objects.filter(
        enrollment=enrollment, session__status=AttendanceSession.Status.FINALIZED
    )
    attendance_counts = attendance_records.aggregate(
        total=Count("id"),
        present=Count("id", filter=Q(status=AttendanceRecord.Status.PRESENT)),
        unexcused=Count("id", filter=Q(status=AttendanceRecord.Status.ABSENT_UNEXCUSED)),
        excused=Count("id", filter=Q(status=AttendanceRecord.Status.ABSENT_EXCUSED)),
        late=Count("id", filter=Q(late_minutes__gt=0)),
    )
    total_records = attendance_counts["total"] or 0
    attendance = {
        "finalized_session_count": attendance_records.values("session_id").distinct().count(),
        "record_count": total_records,
        "present_count": attendance_counts["present"] or 0,
        "unexcused_absence_count": attendance_counts["unexcused"] or 0,
        "excused_absence_count": attendance_counts["excused"] or 0,
        "late_count": attendance_counts["late"] or 0,
        "attendance_rate": round((attendance_counts["present"] or 0) * 100 / total_records, 1)
        if total_records
        else None,
    }
    evaluations = []
    evaluation_rows = list(
        MonthlyEvaluation.objects.filter(enrollment=enrollment)
        .prefetch_related("metric_scores")
        .order_by("month_no", "framework_version")
    )
    for item in evaluation_rows:
        score_rows = list(item.metric_scores.all())
        catalog = metric_catalog_for(item.framework_version) or METRIC_CATALOG
        evaluations.append(
            {
                "month_no": item.month_no,
                "framework_version": item.framework_version,
                "metric_scores": {score.metric_code: score.value for score in score_rows},
                "metrics": [
                    {
                        "code": score.metric_code,
                        "title": catalog.get(score.metric_code, {}).get("title", score.metric_code),
                        "domain_code": catalog.get(score.metric_code, {}).get("domain_code", ""),
                        "domain_title": catalog.get(score.metric_code, {}).get("domain_title", ""),
                        "value": score.value,
                    }
                    for score in score_rows
                ],
            }
        )

    # EvaluationAnalyticsService is the canonical source for the nine-domain
    # analysis.  Keep its result inside the frozen, report-safe snapshot rather
    # than re-implementing the weighted calculation in presentation code.  The
    # service only reads MonthlyEvaluation/MetricScore and never touches the
    # counseling bounded context.
    analysis = EvaluationAnalyticsService.student_summary(enrollment, rank_scope="class")
    public_analysis = {
        key: analysis[key]
        for key in (
            "completion_status",
            "completion_percent",
            "overall_score",
            "performance_level",
            "first_month",
            "last_month",
            "change",
            "trend",
            "trend_label",
            "recommendation",
            "completion_warning",
            "rank_scope",
            "rank",
            "ranked_count",
        )
    }
    public_analysis["domain_scores"] = _canonical_domain_scores(analysis.get("domain_scores"))
    public_analysis["monthly_scores"] = analysis["monthly_scores"]
    public_analysis["strongest_domain"] = analysis["strongest_domain"]
    public_analysis["weakest_domain"] = analysis["weakest_domain"]
    latest_evaluation = evaluations[-1] if evaluations else None
    behavior = [
        {
            "event_type": item.event_type.code,
            "polarity": item.polarity,
            "severity": item.severity,
            "status": item.status,
            "occurred_at": item.occurred_at.isoformat(),
        }
        for item in BehaviorEvent.objects.filter(
            enrollment=enrollment,
            status__in=[
                BehaviorEvent.Status.CONFIRMED,
                BehaviorEvent.Status.UNDER_FOLLOW_UP,
                BehaviorEvent.Status.RESOLVED,
            ],
        ).select_related("event_type")
    ]
    activities = [
        {
            "title": item.activity.title,
            "kind": item.activity.kind,
            "status": item.status,
            "result": item.result,
            "placement": item.placement,
        }
        for item in ActivityParticipation.objects.filter(enrollment=enrollment).select_related(
            "activity"
        )
    ]
    signals = [
        {
            "rule_code": item.rule_code,
            "rule_version": item.rule_version,
            "severity": item.severity,
            "evidence": item.evidence,
            "explanation": item.explanation,
            "window": item.window,
        }
        for item in StudentRiskSignal.objects.filter(
            enrollment=enrollment, state=StudentRiskSignal.State.ACTIVE
        )
    ]
    recommendations = [
        {
            "audience": item.audience,
            "rule_code": item.rule_code,
            "rule_version": item.rule_version,
            "priority": item.priority,
            "approved_text": item.approved_text,
        }
        for item in Recommendation.objects.filter(
            enrollment=enrollment, status=Recommendation.Status.APPROVED
        ).exclude(audience=Recommendation.Audience.COUNSELOR)
    ]
    return {
        "attendance": attendance,
        "evaluations": evaluations,
        "evaluation_analysis": public_analysis,
        "latest_evaluation": latest_evaluation,
        "behavior_events": behavior,
        "activities": activities,
        "analytics_signals": signals,
        "approved_recommendations": recommendations,
        # This key is intentionally independent from recommendations.  A
        # school may choose to record family-support guidance separately; an
        # empty list means it was not supplied, not that a recommendation is
        # suitable for the family-support panel.
        "support_notes": [],
    }


def build_draft_snapshot(template, *, term, enrollment=None, class_section=None):
    """Freeze all report inputs at draft creation; counseling is intentionally absent."""
    snapshot = build_report_snapshot(
        template.report_type,
        term,
        enrollment=enrollment,
        class_section=class_section,
    )
    enrollments = (
        [enrollment]
        if enrollment
        else list(
            Enrollment.all_objects.filter(
                class_section=class_section,
                enrolled_on__lte=term.ends_on,
                is_deleted=False,
            )
            .filter(Q(left_on__isnull=True) | Q(left_on__gte=term.starts_on))
            .select_related("student")
        )
    )
    for report, subject in zip(snapshot["reports"], enrollments, strict=True):
        report["product_context"] = _report_extended_context(subject)
    presentation = dict(template.presentation or {})
    presentation["page_size"] = normalize_report_page_size(presentation.get("page_size"))
    snapshot["template"] = {
        "id": str(template.id),
        "code": template.code,
        "blocks": list(template.blocks),
        "presentation": presentation,
        "output_format": template.output_format,
    }
    return snapshot


def render_report_draft(draft_id):
    """Render exactly the frozen approved snapshot into the immutable archive."""
    with transaction.atomic():
        draft = (
            # enrollment and class_section are deliberately nullable (a draft
            # has exactly one of them). PostgreSQL rejects a plain FOR UPDATE
            # over the nullable side of the resulting outer join, so lock only
            # the draft row that protects this state transition.
            ReportDraft.objects.select_for_update(of=("self",))
            .select_related(
                "template",
                "organization",
                "school",
                "academic_year",
                "term",
                "enrollment",
                "class_section",
            )
            .get(pk=draft_id)
        )
        if draft.status == ReportDraft.Status.RENDERED:
            return draft
        if draft.status != ReportDraft.Status.APPROVED:
            raise ValueError("Only an approved report draft may be rendered.")
        render_snapshot = deepcopy(draft.snapshot)
        render_snapshot["content_overrides"] = dict(draft.content_overrides)
        archive = ReportArchive.objects.create(
            organization=draft.organization,
            school=draft.school,
            academic_year=draft.academic_year,
            term=draft.term,
            report_type=draft.template.report_type,
            status=ReportArchive.Status.PROCESSING,
            enrollment=draft.enrollment,
            class_section=draft.class_section,
            requested_by=draft.created_by,
            output_format=draft.template.output_format,
            snapshot=render_snapshot,
            formula_version=(render_snapshot.get("reports") or [{}])[0]
            .get("summary", {})
            .get("formula_version", ""),
            started_at=timezone.now(),
        )
    try:
        if draft.template.output_format == draft.template.OutputFormat.DOCX:
            output = render_report_docx(render_snapshot)
            extension = "docx"
        else:
            output = render_report_pdf(render_snapshot)
            extension = "pdf"
        filename = f"draft_{draft.id}_{draft.created_at:%Y-%m-%d}.{extension}"
        archive.output_file.save(filename, ContentFile(output), save=False)
        output_name = archive.output_file.name
        with transaction.atomic():
            archive = ReportArchive.objects.select_for_update().get(pk=archive.pk)
            archive.output_file.name = output_name
            archive.status = ReportArchive.Status.COMPLETED
            archive.completed_at = timezone.now()
            archive.error_message = ""
            archive.save(
                update_fields=[
                    "output_file",
                    "status",
                    "completed_at",
                    "error_message",
                    "updated_at",
                ]
            )
            draft = ReportDraft.objects.select_for_update().get(pk=draft_id)
            draft.status = ReportDraft.Status.RENDERED
            draft.archive = archive
            draft.save(update_fields=["status", "archive", "updated_at"])
            return draft
    except Exception as exc:
        archive.status = ReportArchive.Status.FAILED
        archive.error_message = str(exc)[:2000]
        archive.completed_at = timezone.now()
        archive.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        raise


def generate_report(report_id):
    processing_timeout = timedelta(
        minutes=getattr(settings, "REPORT_PROCESSING_TIMEOUT_MINUTES", 30)
    )
    with transaction.atomic():
        report = (
            ReportArchive.objects.select_for_update(of=("self",))
            .select_related("term", "enrollment", "class_section")
            .get(pk=report_id)
        )
        if report.status == ReportArchive.Status.COMPLETED:
            return report
        if (
            report.status == ReportArchive.Status.PROCESSING
            and report.started_at
            and report.started_at >= timezone.now() - processing_timeout
        ):
            return report
        report.status = ReportArchive.Status.PROCESSING
        report.started_at = timezone.now()
        report.completed_at = None
        report.error_message = ""
        report.save(
            update_fields=[
                "status",
                "started_at",
                "completed_at",
                "error_message",
                "updated_at",
            ]
        )

    stored_name = ""
    try:
        snapshot = build_report_render_snapshot(
            report.report_type,
            report.term,
            enrollment=report.enrollment,
            class_section=report.class_section,
            report_mode=report.report_mode,
            month_no=report.month_no,
        )
        pdf = render_report_pdf(snapshot)
        first = snapshot["reports"][0] if snapshot["reports"] else None
        formula_version = first["summary"]["formula_version"] if first else ""
        filename = (
            f"{report.report_type}_"
            f"{report.organization.code}_"
            f"{report.school.code}_"
            f"{report.created_at:%Y-%m-%d}.pdf"
        )
        report.output_file.save(filename, ContentFile(pdf), save=False)
        stored_name = report.output_file.name
        with transaction.atomic():
            locked = ReportArchive.objects.select_for_update().get(pk=report_id)
            if locked.status == ReportArchive.Status.COMPLETED:
                if stored_name and stored_name != locked.output_file.name:
                    report.output_file.storage.delete(stored_name)
                return locked
            locked.output_file = report.output_file
            locked.snapshot = snapshot
            locked.formula_version = formula_version
            locked.status = ReportArchive.Status.COMPLETED
            locked.completed_at = timezone.now()
            locked.error_message = ""
            locked.save()
            return locked
    except Exception as exc:
        if stored_name:
            report.output_file.storage.delete(stored_name)
        with transaction.atomic():
            locked = ReportArchive.objects.select_for_update().get(pk=report_id)
            locked.status = ReportArchive.Status.FAILED
            locked.error_message = str(exc)[:2000]
            locked.completed_at = timezone.now()
            locked.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        raise
