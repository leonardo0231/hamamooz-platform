from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

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
from hamamooz.apps.students.models import Enrollment

from .models import ReportArchive


def _category_averages(enrollment, offering, policy):
    buckets = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    scores = Score.objects.filter(
        enrollment=enrollment,
        assessment__course_offering=offering,
        assessment__status__in=[Assessment.Status.APPROVED, Assessment.Status.LOCKED],
    ).select_related("assessment", "assessment__assessment_type")
    for score in scores:
        value = normalized_score(score, policy)
        if value is None:
            continue
        category = score.assessment.assessment_type.category
        buckets[category][0] += value * score.assessment.weight
        buckets[category][1] += score.assessment.weight
    return {
        category: quantize(total / weight, policy) if weight else None
        for category, (total, weight) in buckets.items()
    }


def _decimal_string(value, decimal_places=2):
    return f"{value:.{decimal_places}f}" if value is not None else None


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
    offerings = CourseOffering.objects.filter(
        class_section=enrollment.class_section, term=term, is_active=True
    ).select_related("grade_subject__subject")
    result_map = {
        row.course_offering_id: row
        for row in SubjectResult.objects.filter(
            enrollment=enrollment, course_offering__in=offerings
        )
    }
    subjects = []
    for offering in offerings:
        result = result_map.get(offering.id)
        categories = _category_averages(enrollment, offering, policy)
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
                "passed": result.passed if result else False,
            }
        )
    school = enrollment.school
    logo_url = school.logo.url if school.logo else ""
    return {
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


def build_report_snapshot(report_type, term, enrollment=None, class_section=None):
    if report_type == ReportArchive.ReportType.STUDENT_REPORT_CARD:
        return {"reports": [build_student_snapshot(enrollment, term)]}
    enrollments = list(
        Enrollment.objects.filter(
            class_section=class_section, status=Enrollment.Status.ACTIVE
        ).select_related("student", "school", "academic_year", "grade_level", "class_section")
    )
    recalculate_class_term(class_section, term)
    return {
        "reports": [build_student_snapshot(item, term, recalculate=False) for item in enrollments]
    }


def render_report_html(snapshot, *, preview=False):
    return render_to_string(
        "reports/report_card.html",
        {"reports": snapshot["reports"], "preview": preview, "generated_at": timezone.now()},
    )


def _local_media_file_url(url):
    if not url or not url.startswith(settings.MEDIA_URL):
        return url
    relative = url.removeprefix(settings.MEDIA_URL).lstrip("/")
    media_root = Path(settings.MEDIA_ROOT).resolve()
    candidate = (media_root / relative).resolve()
    if not candidate.is_relative_to(media_root):
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
    html = render_report_html(_pdf_snapshot(snapshot))
    return HTML(string=html, base_url=Path(settings.BASE_DIR).as_uri()).write_pdf(
        presentational_hints=False
    )


def generate_report(report_id):
    with transaction.atomic():
        report = (
            ReportArchive.objects.select_for_update()
            .select_related("term", "enrollment", "class_section")
            .get(pk=report_id)
        )
        if report.status == ReportArchive.Status.COMPLETED:
            return report
        report.status = ReportArchive.Status.PROCESSING
        report.started_at = timezone.now()
        report.error_message = ""
        report.save(update_fields=["status", "started_at", "error_message", "updated_at"])
    try:
        snapshot = build_report_snapshot(
            report.report_type,
            report.term,
            enrollment=report.enrollment,
            class_section=report.class_section,
        )
        pdf = render_report_pdf(snapshot)
        first = snapshot["reports"][0] if snapshot["reports"] else None
        formula_version = first["summary"]["formula_version"] if first else ""
        filename = f"{report.report_type}_{report.id}.pdf"
        report.output_file.save(filename, ContentFile(pdf), save=False)
        report.snapshot = snapshot
        report.formula_version = formula_version
        report.status = ReportArchive.Status.COMPLETED
        report.completed_at = timezone.now()
        with transaction.atomic():
            report.save()
    except Exception as exc:
        with transaction.atomic():
            report = ReportArchive.objects.select_for_update().get(pk=report_id)
            report.status = ReportArchive.Status.FAILED
            report.error_message = str(exc)[:2000]
            report.completed_at = timezone.now()
            report.save()
        raise
    return report
