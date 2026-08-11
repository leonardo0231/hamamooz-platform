from hamamooz.apps.academics.models import SubjectResult, TermResult
from hamamooz.apps.attendance.selectors import enrollment_metrics
from hamamooz.apps.evaluations.catalog import FRAMEWORK_VERSION
from hamamooz.apps.evaluations.models import MonthlyEvaluation
from hamamooz.apps.reports.models import ReportArchive
from hamamooz.apps.students.models import Enrollment


def visible_student_enrollments(*, student, school_ids, class_ids) -> list[Enrollment]:
    return list(
        Enrollment.objects.filter(
            student=student,
            school_id__in=school_ids,
            class_section_id__in=class_ids,
        )
        .select_related("school", "academic_year", "grade_level", "class_section")
        .order_by("-academic_year__starts_on", "-enrolled_on")
    )


def current_visible_student_enrollment(*, student, school_ids, class_ids) -> Enrollment | None:
    enrollments = visible_student_enrollments(
        student=student,
        school_ids=school_ids,
        class_ids=class_ids,
    )
    return next(
        (enrollment for enrollment in enrollments if enrollment.status == Enrollment.Status.ACTIVE),
        enrollments[0] if enrollments else None,
    )


def build_student_360_summary(*, student, school_ids, class_ids) -> dict:
    """Compose only the visible identity and enrollment context for Student 360."""
    enrollments = visible_student_enrollments(
        student=student,
        school_ids=school_ids,
        class_ids=class_ids,
    )
    current_enrollment = next(
        (enrollment for enrollment in enrollments if enrollment.status == Enrollment.Status.ACTIVE),
        enrollments[0] if enrollments else None,
    )

    return {
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "status": student.status,
        },
        "current_enrollment": (
            {
                "id": current_enrollment.id,
                "student_number": current_enrollment.student_number,
                "school": current_enrollment.school.name,
                "academic_year": current_enrollment.academic_year.title,
                "grade": current_enrollment.grade_level.title,
                "class_section": current_enrollment.class_section.title,
                "status": current_enrollment.status,
            }
            if current_enrollment
            else None
        ),
    }


def build_student_360_attendance(*, student, school_ids, class_ids) -> dict:
    enrollment = current_visible_student_enrollment(
        student=student,
        school_ids=school_ids,
        class_ids=class_ids,
    )
    if enrollment is None:
        return {"enrollment": None, "date_from": None, "date_to": None, "metrics": None}
    date_from = enrollment.academic_year.starts_on
    date_to = enrollment.academic_year.ends_on
    return {
        "enrollment": enrollment.id,
        "date_from": date_from,
        "date_to": date_to,
        "metrics": enrollment_metrics(
            enrollment=enrollment,
            date_from=date_from,
            date_to=date_to,
            include_excused=True,
        ),
    }


def build_student_360_evaluations(*, student, school_ids, class_ids) -> dict:
    enrollments = visible_student_enrollments(
        student=student,
        school_ids=school_ids,
        class_ids=class_ids,
    )
    evaluations = (
        MonthlyEvaluation.objects.filter(
            enrollment_id__in=[enrollment.id for enrollment in enrollments]
        )
        .select_related(
            "enrollment__student",
            "enrollment__school__organization",
            "enrollment__academic_year",
            "enrollment__class_section",
            "recorded_by",
            "source_import_job",
        )
        .prefetch_related("metric_scores")
        .order_by("-month_no")
    )
    return {"framework_version": FRAMEWORK_VERSION, "evaluations": evaluations}


def build_student_360_reports(*, student, school_ids, class_ids) -> dict:
    enrollments = visible_student_enrollments(
        student=student,
        school_ids=school_ids,
        class_ids=class_ids,
    )
    reports = ReportArchive.objects.filter(
        enrollment_id__in=[enrollment.id for enrollment in enrollments]
    ).select_related(
        "organization",
        "school",
        "academic_year",
        "term",
        "enrollment__student",
        "class_section",
        "requested_by",
    )
    return {"reports": reports}


def build_student_360_behavior(*, student, school_ids, class_ids) -> dict:
    # Behavior is an optional later bounded context.  The F1 composition must
    # remain readable before that app is installed, and must not manufacture
    # an evaluation score from an event.
    try:
        from hamamooz.apps.behavior.models import BehaviorEvent
    except (ImportError, LookupError):
        return {"events": []}

    enrollments = visible_student_enrollments(
        student=student,
        school_ids=school_ids,
        class_ids=class_ids,
    )
    events = (
        BehaviorEvent.objects.filter(
            enrollment_id__in=[enrollment.id for enrollment in enrollments],
            status__in=[
                BehaviorEvent.Status.CONFIRMED,
                BehaviorEvent.Status.UNDER_FOLLOW_UP,
                BehaviorEvent.Status.RESOLVED,
            ],
        )
        .select_related("event_type")
        .order_by("-occurred_at")
    )
    return {
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type.title,
                "polarity": event.polarity,
                "severity": event.severity,
                "status": event.status,
            }
            for event in events
        ]
    }


def build_student_360_activities(*, student, school_ids, class_ids) -> dict:
    # Activities joins the 360 composition in F2; return an explicit empty
    # section until the bounded context is available.
    try:
        from hamamooz.apps.activities.models import ActivityParticipation
    except (ImportError, LookupError):
        return {"participations": []}

    enrollments = visible_student_enrollments(
        student=student,
        school_ids=school_ids,
        class_ids=class_ids,
    )
    participations = (
        ActivityParticipation.objects.filter(
            enrollment_id__in=[enrollment.id for enrollment in enrollments]
        )
        .select_related("activity")
        .order_by("-activity__starts_at")
    )
    return {
        "participations": [
            {
                "id": participation.id,
                "activity": participation.activity.title,
                "kind": participation.activity.kind,
                "status": participation.status,
                "participation_role": participation.participation_role,
                "result": participation.result,
                "placement": participation.placement,
            }
            for participation in participations
        ]
    }


def build_student_360_risks(*, student, school_ids, class_ids) -> dict:
    # Analytics is introduced after the evidence-producing domains.  Keeping
    # this import local prevents F1 from gaining a hidden app dependency.
    try:
        from hamamooz.apps.analytics.models import StudentRiskSignal
    except (ImportError, LookupError):
        return {"signals": []}

    enrollments = visible_student_enrollments(
        student=student,
        school_ids=school_ids,
        class_ids=class_ids,
    )
    signals = StudentRiskSignal.objects.filter(
        enrollment_id__in=[enrollment.id for enrollment in enrollments],
        state=StudentRiskSignal.State.ACTIVE,
    ).order_by("-created_at")
    return {
        "signals": [
            {
                "id": signal.id,
                "rule_code": signal.rule_code,
                "rule_version": signal.rule_version,
                "severity": signal.severity,
                "evidence": signal.evidence,
                "explanation": signal.explanation,
                "window": signal.window,
                "created_at": signal.created_at,
            }
            for signal in signals
        ]
    }


def build_student_360_recommendations(
    *, student, school_ids, class_ids, recommendation_queryset=None
) -> dict:
    # Recommendation visibility is tightened by F5.  Before that app exists,
    # a 360 caller receives no recommendation data rather than an error or a
    # client-side confidentiality filter.
    if recommendation_queryset is None:
        try:
            from hamamooz.apps.recommendations.models import Recommendation
        except (ImportError, LookupError):
            return {"recommendations": []}
        recommendation_queryset = Recommendation.objects.none()

    enrollments = visible_student_enrollments(
        student=student,
        school_ids=school_ids,
        class_ids=class_ids,
    )
    recommendations = recommendation_queryset.filter(
        enrollment_id__in=[enrollment.id for enrollment in enrollments]
    ).order_by("-created_at")
    return {
        "recommendations": [
            {
                "id": recommendation.id,
                "audience": recommendation.audience,
                "priority": recommendation.priority,
                "status": recommendation.status,
                "rule_code": recommendation.rule_code,
                "rule_version": recommendation.rule_version,
                "generated_text": recommendation.generated_text,
                "approved_text": recommendation.approved_text,
                "approved_at": recommendation.approved_at,
            }
            for recommendation in recommendations
        ]
    }


def build_student_360_academics(*, student, school_ids, class_ids) -> dict:
    enrollments = visible_student_enrollments(
        student=student,
        school_ids=school_ids,
        class_ids=class_ids,
    )
    enrollment_ids = [enrollment.id for enrollment in enrollments]
    term_results = (
        TermResult.objects.filter(enrollment_id__in=enrollment_ids)
        .select_related("term")
        .order_by("-term__academic_year__starts_on", "term__order")
    )
    subject_results = (
        SubjectResult.objects.filter(enrollment_id__in=enrollment_ids)
        .select_related("course_offering__grade_subject__subject")
        .order_by("course_offering__grade_subject__subject__title")
    )

    return {
        "term_results": [
            {
                "enrollment": result.enrollment_id,
                "term": {"id": result.term_id, "title": result.term.title},
                "average": float(result.average) if result.average is not None else None,
                "class_rank": result.class_rank,
                "passed": result.passed,
                "formula_version": result.formula_version,
            }
            for result in term_results
        ],
        "subject_results": [
            {
                "enrollment": result.enrollment_id,
                "subject": result.course_offering.grade_subject.subject.title,
                "average": float(result.average) if result.average is not None else None,
                "passed": result.passed,
                "formula_version": result.formula_version,
            }
            for result in subject_results
        ],
    }
