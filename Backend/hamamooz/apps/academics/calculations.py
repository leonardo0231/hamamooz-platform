from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from django.db import transaction

from hamamooz.apps.students.models import Enrollment

from .models import (
    Assessment,
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


@transaction.atomic
def calculate_enrollment_term(enrollment, term):
    policy = get_policy(enrollment)
    offerings = CourseOffering.objects.filter(
        class_section=enrollment.class_section,
        term=term,
        is_active=True,
    ).select_related("grade_subject", "grade_subject__subject")
    subject_rows = []
    for offering in offerings:
        scores = Score.objects.filter(
            enrollment=enrollment,
            assessment__course_offering=offering,
            assessment__status__in=[Assessment.Status.APPROVED, Assessment.Status.LOCKED],
        ).select_related("assessment")
        numerator = Decimal("0")
        denominator = Decimal("0")
        for score in scores:
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
    passed = (
        term_average is not None
        and term_average >= policy.overall_pass_mark
        and all(row.passed for row in subject_rows if row.average is not None)
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
        Enrollment.objects.filter(
            class_section=class_section, status=Enrollment.Status.ACTIVE
        ).select_related("student", "academic_year", "grade_level")
    )
    results = [calculate_enrollment_term(enrollment, term) for enrollment in enrollments]
    ranked = sorted(
        [result for result in results if result.average is not None],
        key=lambda r: r.average,
        reverse=True,
    )
    rank = 0
    previous = None
    for index, result in enumerate(ranked, start=1):
        if previous is None or result.average != previous:
            rank = index
        result.class_rank = rank
        result.save(update_fields=["class_rank", "updated_at"])
        previous = result.average
    TermResult.objects.filter(
        enrollment__class_section=class_section, term=term, average__isnull=True
    ).update(class_rank=None)
    return results
