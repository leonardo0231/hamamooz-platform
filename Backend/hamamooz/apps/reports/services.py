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
from django.db.models import Q
from django.template.loader import render_to_string
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
# influencing @page with arbitrary text.
ALLOWED_REPORT_PAGE_SIZES = {
    "a4_portrait": "A4 portrait",
    "a3_landscape": "A3 landscape",
}


def report_page_size(presentation):
    """Return a safe CSS @page value for a frozen template presentation."""
    if not isinstance(presentation, dict):
        return ALLOWED_REPORT_PAGE_SIZES["a4_portrait"]
    return ALLOWED_REPORT_PAGE_SIZES.get(
        presentation.get("page_size"), ALLOWED_REPORT_PAGE_SIZES["a4_portrait"]
    )


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
                "passed": result.passed if result else False,
            }
        )
    school = enrollment.school
    logo_url = school.logo.url if school.logo else ""
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


def build_analytical_snapshot(enrollment, term, *, page_size="a3_landscape"):
    """Frozen snapshot for the coloured student report and its in-app view."""
    snapshot = build_report_snapshot(
        ReportArchive.ReportType.STUDENT_REPORT_CARD, term, enrollment=enrollment
    )
    report = snapshot["reports"][0]
    report["product_context"] = _report_extended_context(enrollment)
    history = (
        TermResult.objects.filter(enrollment__student=enrollment.student)
        .select_related("term", "enrollment__academic_year")
        .order_by("-enrollment__academic_year__starts_on", "-term__ends_on")[:3]
    )
    report["history"] = [
        {"label": item.enrollment.academic_year.title, "average": _decimal_string(item.average)}
        for item in reversed(history)
        if item.average is not None
    ]
    snapshot["template"] = {
        "blocks": list(ALLOWED_REPORT_BLOCKS),
        "presentation": {"page_size": page_size},
    }
    return snapshot


def render_report_batch(batch_id):
    """Render every queued item independently, then package successful PDFs."""
    batch = ReportBatch.objects.select_related("organization", "school", "academic_year", "term", "requested_by").get(pk=batch_id)
    batch.status = ReportBatch.Status.PROCESSING
    batch.started_at = timezone.now()
    batch.save(update_fields=["status", "started_at", "updated_at"])
    output = BytesIO()
    completed = failed = 0
    with ZipFile(output, "w", ZIP_DEFLATED) as archive_zip:
        for item in batch.items.select_related("enrollment__student", "enrollment__class_section").all():
            item.status = ReportBatchItem.Status.PROCESSING
            item.save(update_fields=["status", "updated_at"])
            try:
                snapshot = build_analytical_snapshot(batch_item_enrollment := item.enrollment, batch.term, page_size=batch.page_size)
                report = ReportArchive.objects.create(
                    organization=batch.organization, school=batch.school, academic_year=batch.academic_year,
                    term=batch.term, report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
                    status=ReportArchive.Status.PROCESSING, enrollment=batch_item_enrollment,
                    requested_by=batch.requested_by, output_format=ReportArchive.OutputFormat.PDF,
                    snapshot=snapshot, started_at=timezone.now(),
                )
                pdf = render_report_pdf(snapshot)
                safe_id = batch_item_enrollment.student.national_id or str(batch_item_enrollment.student_id)
                filename = f"{safe_id}-{batch_item_enrollment.student.full_name}.pdf".replace("/", "-")
                report.output_file.save(filename, ContentFile(pdf), save=False)
                report.status = ReportArchive.Status.COMPLETED
                report.completed_at = timezone.now()
                report.formula_version = snapshot["reports"][0]["summary"]["formula_version"]
                report.save()
                report.output_file.open("rb")
                archive_zip.writestr(filename, report.output_file.read())
                item.report, item.status, item.error_message = report, ReportBatchItem.Status.COMPLETED, ""
                item.save(update_fields=["report", "status", "error_message", "updated_at"])
                completed += 1
            except Exception as exc:  # one student must never abort a school batch
                item.status, item.error_message = ReportBatchItem.Status.FAILED, str(exc)[:2000]
                item.save(update_fields=["status", "error_message", "updated_at"])
                failed += 1
    batch.completed_count, batch.failed_count = completed, failed
    batch.completed_at = timezone.now()
    batch.status = ReportBatch.Status.COMPLETED if failed == 0 else (ReportBatch.Status.PARTIAL if completed else ReportBatch.Status.FAILED)
    if completed:
        batch.zip_file.save(f"report-batch-{batch.id}.zip", ContentFile(output.getvalue()), save=False)
    batch.save()
    return batch


def render_report_html(snapshot, *, preview=False):
    template = snapshot.get("template", {})
    return render_to_string(
        "reports/report_card.html",
        {
            "reports": snapshot["reports"],
            "preview": preview,
            "blocks": template.get("blocks", ALLOWED_REPORT_BLOCKS),
            "overrides": snapshot.get("content_overrides", {}),
            "page_size": report_page_size(template.get("presentation")),
            "generated_at": timezone.now(),
        },
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
    from weasyprint import HTML

    html = render_report_html(_pdf_snapshot(snapshot))
    return HTML(
        string=html,
        base_url=Path(settings.BASE_DIR).as_uri(),
    ).write_pdf(presentational_hints=False)


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
    from hamamooz.apps.evaluations.models import MonthlyEvaluation
    from hamamooz.apps.recommendations.models import Recommendation

    attendance_records = AttendanceRecord.objects.filter(
        enrollment=enrollment, session__status=AttendanceSession.Status.FINALIZED
    )
    attendance = {
        "finalized_session_count": attendance_records.values("session_id").distinct().count(),
        "unexcused_absence_count": attendance_records.filter(
            status=AttendanceRecord.Status.ABSENT_UNEXCUSED
        ).count(),
    }
    evaluations = [
        {
            "month_no": item.month_no,
            "framework_version": item.framework_version,
            "metric_scores": {score.metric_code: score.value for score in item.metric_scores.all()},
        }
        for item in MonthlyEvaluation.objects.filter(enrollment=enrollment)
        .prefetch_related("metric_scores")
        .order_by("month_no", "framework_version")
    ]
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
        "behavior_events": behavior,
        "activities": activities,
        "analytics_signals": signals,
        "approved_recommendations": recommendations,
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
    snapshot["template"] = {
        "id": str(template.id),
        "code": template.code,
        "blocks": list(template.blocks),
        "presentation": template.presentation,
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
        snapshot = build_report_snapshot(
            report.report_type,
            report.term,
            enrollment=report.enrollment,
            class_section=report.class_section,
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
