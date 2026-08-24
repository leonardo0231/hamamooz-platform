from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from hamamooz.apps.organizations.models import ClassSection, Term
from hamamooz.apps.students.models import Enrollment

from .models import (
    AcademicReportSettings,
    Assessment,
    AnnualResult,
    AnnualSubjectResult,
    CalculationPolicy,
    CourseOffering,
    Score,
    SubjectResult,
    TermResult,
)


@dataclass(frozen=True)
class EffectivePolicy:
    version: str = "mvp-default-v1"
    overall_pass_mark: Decimal = Decimal("10")
    decimal_places: int = 2
    rounding_mode: str = CalculationPolicy.RoundingMode.HALF_UP
    unexcused_absence_as_zero: bool = True


def get_policy(enrollment):
    organization_id = enrollment.student.organization_id
    candidates = [
        (enrollment.academic_year_id, enrollment.grade_level_id),
        (enrollment.academic_year_id, None),
        (None, enrollment.grade_level_id),
        (None, None),
    ]
    for academic_year_id, grade_level_id in candidates:
        policy = (
            CalculationPolicy.objects.filter(
                organization_id=organization_id,
                academic_year_id=academic_year_id,
                grade_level_id=grade_level_id,
                is_active=True,
            )
            .order_by("-created_at")
            .first()
        )
        if policy:
            return EffectivePolicy(
                version=policy.version,
                overall_pass_mark=policy.overall_pass_mark,
                decimal_places=policy.decimal_places,
                rounding_mode=policy.rounding_mode,
                unexcused_absence_as_zero=policy.unexcused_absence_as_zero,
            )
    return EffectivePolicy()


def quantize(value, policy):
    if value is None:
        return None
    rounding = {
        CalculationPolicy.RoundingMode.HALF_UP: ROUND_HALF_UP,
        CalculationPolicy.RoundingMode.HALF_EVEN: ROUND_HALF_EVEN,
        CalculationPolicy.RoundingMode.DOWN: ROUND_DOWN,
    }[policy.rounding_mode]
    unit = Decimal("1").scaleb(-policy.decimal_places)
    return value.quantize(unit, rounding=rounding)


def normalized_score(score, policy):
    if score.status == Score.Status.PRESENT:
        return score.value * Decimal("20") / score.assessment.max_score
    if score.status == Score.Status.UNEXCUSED_ABSENT and policy.unexcused_absence_as_zero:
        return Decimal("0")
    return None


def get_academic_report_settings(school, academic_year):
    configured = AcademicReportSettings.objects.filter(
        school=school,
        academic_year=academic_year,
    ).first()
    if configured:
        return configured
    return AcademicReportSettings(
        school=school,
        academic_year=academic_year,
        first_term_weight=Decimal("1"),
        second_term_weight=Decimal("2"),
        show_class_rank=True,
        show_grade_rank=True,
        show_school_rank=True,
    )


def _dense_rank(rows, *, rank_field, population_field):
    population = len(rows)
    for row in rows:
        setattr(row, rank_field, None)
        setattr(row, population_field, population)
    ranked = sorted(
        (row for row in rows if row.average is not None),
        key=lambda row: (-row.average, str(row.enrollment_id)),
    )
    rank = 0
    previous = None
    for row in ranked:
        if previous is None or row.average != previous:
            rank += 1
        setattr(row, rank_field, rank)
        previous = row.average


def _apply_three_scope_ranks(results):
    by_class = defaultdict(list)
    by_grade = defaultdict(list)
    for result in results:
        by_class[result.enrollment.class_section_id].append(result)
        by_grade[result.enrollment.grade_level_id].append(result)
    for rows in by_class.values():
        _dense_rank(rows, rank_field="class_rank", population_field="class_population")
    for rows in by_grade.values():
        _dense_rank(rows, rank_field="grade_rank", population_field="grade_population")
    _dense_rank(results, rank_field="school_rank", population_field="school_population")


def _annual_anchor(enrollment):
    return (
        Enrollment.objects.filter(
            student_id=enrollment.student_id,
            school_id=enrollment.school_id,
            academic_year_id=enrollment.academic_year_id,
            grade_level_id=enrollment.grade_level_id,
            status=Enrollment.Status.ACTIVE,
        )
        .order_by("-enrolled_on", "-created_at", "-pk")
        .first()
        or enrollment
    )


@transaction.atomic
def calculate_enrollment_annual(enrollment):
    anchor = _annual_anchor(enrollment)
    policy = get_policy(anchor)
    report_settings = get_academic_report_settings(anchor.school, anchor.academic_year)
    historical_enrollments = list(
        Enrollment.all_objects.filter(
            student_id=anchor.student_id,
            school_id=anchor.school_id,
            academic_year_id=anchor.academic_year_id,
            grade_level_id=anchor.grade_level_id,
            is_deleted=False,
        ).select_related("class_section")
    )
    historical_ids = [item.id for item in historical_enrollments]
    required_terms = list(
        Term.objects.filter(
            academic_year_id=anchor.academic_year_id,
            code__in=[Term.Code.FIRST, Term.Code.SECOND],
        ).order_by("order", "pk")
    )
    eligible_class_term_pairs = {
        (historical.class_section_id, term.id)
        for historical in historical_enrollments
        for term in required_terms
        if historical.enrolled_on <= term.ends_on
        and (historical.left_on is None or historical.left_on >= term.starts_on)
    }
    eligible_offerings = CourseOffering.objects.filter(
        class_section_id__in={item[0] for item in eligible_class_term_pairs},
        term_id__in={item[1] for item in eligible_class_term_pairs},
        grade_subject__grade_level_id=anchor.grade_level_id,
        grade_subject__is_active=True,
        is_active=True,
    ).select_related("grade_subject__subject")
    required_subjects_by_id = {
        offering.grade_subject_id: offering.grade_subject
        for offering in eligible_offerings
        if (offering.class_section_id, offering.term_id) in eligible_class_term_pairs
    }
    required_subjects = sorted(
        required_subjects_by_id.values(),
        key=lambda item: (item.subject.title, str(item.pk)),
    )
    if anchor.status == Enrollment.Status.ACTIVE:
        stale_results = AnnualResult.objects.filter(
            enrollment__student_id=anchor.student_id,
            enrollment__school_id=anchor.school_id,
            enrollment__academic_year_id=anchor.academic_year_id,
            enrollment__grade_level_id=anchor.grade_level_id,
        ).exclude(enrollment=anchor)
        AnnualSubjectResult.objects.filter(annual_result__in=stale_results).delete()
        stale_results.delete()
    rows = (
        SubjectResult.objects.filter(
            enrollment_id__in=historical_ids,
            course_offering__term__academic_year_id=anchor.academic_year_id,
            course_offering__term__code__in=[Term.Code.FIRST, Term.Code.SECOND],
            course_offering__grade_subject_id__in=[item.id for item in required_subjects],
        )
        .select_related("course_offering__term", "enrollment")
        .order_by(
            "course_offering__term__order",
            "enrollment__enrolled_on",
            "calculated_at",
            "pk",
        )
    )
    by_subject_term = {}
    for row in rows:
        if (row.enrollment.class_section_id, row.course_offering.term_id) not in (
            eligible_class_term_pairs
        ):
            continue
        key = (row.course_offering.grade_subject_id, row.course_offering.term.code)
        by_subject_term[key] = row

    annual_result, _ = AnnualResult.objects.update_or_create(
        enrollment=anchor,
        defaults={
            "average": None,
            "complete": False,
            "passed": False,
            "formula_version": policy.version,
        },
    )
    annual_subjects = []
    for grade_subject in required_subjects:
        first = by_subject_term.get((grade_subject.id, Term.Code.FIRST))
        second = by_subject_term.get((grade_subject.id, Term.Code.SECOND))
        complete = bool(
            first
            and first.average is not None
            and second
            and second.average is not None
        )
        if complete:
            numerator = (
                first.average * report_settings.first_term_weight
                + second.average * report_settings.second_term_weight
            )
            denominator = (
                report_settings.first_term_weight + report_settings.second_term_weight
            )
            average = quantize(numerator / denominator, policy)
        else:
            average = None
        result, _ = AnnualSubjectResult.objects.update_or_create(
            enrollment=anchor,
            grade_subject=grade_subject,
            defaults={
                "annual_result": annual_result,
                "average": average,
                "complete": complete,
                "passed": bool(complete and average >= grade_subject.pass_mark),
                "formula_version": policy.version,
            },
        )
        annual_subjects.append(result)

    AnnualSubjectResult.objects.filter(annual_result=annual_result).exclude(
        grade_subject_id__in=[item.id for item in required_subjects]
    ).delete()
    complete = bool(annual_subjects) and all(row.complete for row in annual_subjects)
    if complete:
        coefficient_sum = sum(
            (row.grade_subject.coefficient for row in annual_subjects), Decimal("0")
        )
        weighted_sum = sum(
            (row.average * row.grade_subject.coefficient for row in annual_subjects),
            Decimal("0"),
        )
        average = quantize(weighted_sum / coefficient_sum, policy) if coefficient_sum else None
    else:
        average = None
    annual_result.average = average
    annual_result.complete = bool(complete and average is not None)
    annual_result.passed = bool(
        annual_result.complete
        and average >= policy.overall_pass_mark
        and all(row.passed for row in annual_subjects)
    )
    annual_result.formula_version = policy.version
    annual_result.save(
        update_fields=[
            "average",
            "complete",
            "passed",
            "formula_version",
            "calculated_at",
            "updated_at",
        ]
    )
    return annual_result


@transaction.atomic
def calculate_enrollment_term(enrollment, term):
    policy = get_policy(enrollment)
    offerings = list(
        CourseOffering.objects.filter(
            class_section=enrollment.class_section,
            term=term,
            is_active=True,
        ).select_related("grade_subject", "grade_subject__subject")
    )
    offering_map = {offering.id: offering for offering in offerings}
    score_buckets = {offering.id: [] for offering in offerings}
    scores = Score.objects.filter(
        enrollment=enrollment,
        assessment__course_offering_id__in=offering_map,
        assessment__status__in=[Assessment.Status.APPROVED, Assessment.Status.LOCKED],
    ).select_related("assessment")
    for score in scores:
        score_buckets[score.assessment.course_offering_id].append(score)

    subject_rows = []
    for offering in offerings:
        numerator = Decimal("0")
        denominator = Decimal("0")
        for score in score_buckets[offering.id]:
            normalized = normalized_score(score, policy)
            if normalized is None:
                continue
            numerator += normalized * score.assessment.weight
            denominator += score.assessment.weight
        average = quantize(numerator / denominator, policy) if denominator else None
        passed = average is not None and average >= offering.grade_subject.pass_mark
        result, _ = SubjectResult.objects.update_or_create(
            enrollment=enrollment,
            course_offering=offering,
            defaults={
                "average": average,
                "passed": passed,
                "formula_version": policy.version,
            },
        )
        subject_rows.append(result)

    weighted_sum = Decimal("0")
    coefficient_sum = Decimal("0")
    for row in subject_rows:
        if row.average is None:
            continue
        coefficient = row.course_offering.grade_subject.coefficient
        weighted_sum += row.average * coefficient
        coefficient_sum += coefficient
    term_average = quantize(weighted_sum / coefficient_sum, policy) if coefficient_sum else None
    complete = bool(subject_rows) and all(row.average is not None for row in subject_rows)
    passed = (
        complete
        and term_average is not None
        and term_average >= policy.overall_pass_mark
        and all(row.passed for row in subject_rows)
    )
    term_result, _ = TermResult.objects.update_or_create(
        enrollment=enrollment,
        term=term,
        defaults={
            "average": term_average,
            "passed": passed,
            "formula_version": policy.version,
        },
    )
    return term_result


@transaction.atomic
def recalculate_class_term(class_section, term):
    enrollments = list(
        Enrollment.all_objects.filter(
            class_section=class_section,
            enrolled_on__lte=term.ends_on,
            is_deleted=False,
        )
        .filter(Q(left_on__isnull=True) | Q(left_on__gte=term.starts_on))
        .select_related("student", "academic_year", "grade_level")
    )
    results = [calculate_enrollment_term(enrollment, term) for enrollment in enrollments]
    TermResult.objects.filter(
        enrollment__class_section=class_section,
        term=term,
    ).update(class_rank=None, class_population=None)
    ranked = sorted(
        [result for result in results if result.average is not None],
        key=lambda r: r.average,
        reverse=True,
    )
    rank = 0
    previous = None
    population = len(results)
    for result in results:
        result.class_population = population
        result.save(update_fields=["class_population", "updated_at"])
    for result in ranked:
        if previous is None or result.average != previous:
            rank += 1
        result.class_rank = rank
        result.save(update_fields=["class_rank", "updated_at"])
        previous = result.average
    return results


@transaction.atomic
def recalculate_school_term(school, term):
    if term.academic_year.organization_id != school.organization_id:
        raise ValueError("نوبت و شعبه باید متعلق به یک مجموعه باشند.")
    classes = list(
        ClassSection.objects.filter(
            school=school,
            academic_year=term.academic_year,
            is_active=True,
        ).order_by("grade_level__order", "title", "pk")
    )
    for class_section in classes:
        recalculate_class_term(class_section, term)

    active_enrollment_ids = list(
        Enrollment.objects.filter(
            school=school,
            academic_year=term.academic_year,
            status=Enrollment.Status.ACTIVE,
        ).values_list("id", flat=True)
    )
    TermResult.objects.filter(
        enrollment__school=school,
        enrollment__academic_year=term.academic_year,
        term=term,
    ).exclude(enrollment_id__in=active_enrollment_ids).update(
        class_rank=None,
        grade_rank=None,
        school_rank=None,
        class_population=None,
        grade_population=None,
        school_population=None,
    )
    results = list(
        TermResult.objects.filter(
            enrollment_id__in=active_enrollment_ids,
            term=term,
        ).select_related("enrollment")
    )
    _apply_three_scope_ranks(results)
    if results:
        calculated_at = timezone.now()
        for result in results:
            result.updated_at = calculated_at
        TermResult.objects.bulk_update(
            results,
            [
                "class_rank",
                "grade_rank",
                "school_rank",
                "class_population",
                "grade_population",
                "school_population",
                "updated_at",
            ],
        )
    return results


@transaction.atomic
def recalculate_school_annual(school, academic_year):
    if academic_year.organization_id != school.organization_id:
        raise ValueError("سال تحصیلی و شعبه باید متعلق به یک مجموعه باشند.")
    active_enrollments = list(
        Enrollment.objects.filter(
            school=school,
            academic_year=academic_year,
            status=Enrollment.Status.ACTIVE,
        )
        .select_related("student", "school", "academic_year", "grade_level", "class_section")
        .order_by("grade_level__order", "class_section__title", "student__last_name", "pk")
    )
    active_ids = [item.id for item in active_enrollments]
    AnnualResult.objects.filter(
        enrollment__school=school,
        enrollment__academic_year=academic_year,
    ).exclude(enrollment_id__in=active_ids).update(
        class_rank=None,
        grade_rank=None,
        school_rank=None,
        class_population=None,
        grade_population=None,
        school_population=None,
    )
    results = [calculate_enrollment_annual(enrollment) for enrollment in active_enrollments]
    results = list(
        AnnualResult.objects.filter(pk__in=[item.pk for item in results]).select_related(
            "enrollment"
        )
    )
    _apply_three_scope_ranks(results)
    if results:
        calculated_at = timezone.now()
        for result in results:
            result.updated_at = calculated_at
        AnnualResult.objects.bulk_update(
            results,
            [
                "class_rank",
                "grade_rank",
                "school_rank",
                "class_population",
                "grade_population",
                "school_population",
                "updated_at",
            ],
        )
    return results
