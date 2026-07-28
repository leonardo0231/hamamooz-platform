from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from hamamooz.apps.academics.calculations import (
    get_policy,
    normalized_score,
    quantize,
    recalculate_class_term,
)
from hamamooz.apps.academics.models import (
    Assessment,
    CalculationPolicy,
    Score,
    ScoreRevision,
    TermResult,
)
from hamamooz.apps.academics.services import (
    approve_assessment,
    bulk_upsert_scores,
    correct_locked_score,
    lock_assessment,
    reject_assessment,
    submit_assessment,
)
from hamamooz.apps.students.models import Enrollment, Student


def make_assessment(base_data, *, title="ارزیابی", assessment_type=None, weight="1"):
    return Assessment.objects.create(
        course_offering=base_data["offering1"],
        assessment_type=assessment_type or base_data["continuous"],
        title=title,
        assessment_date=date(2026, 10, 10),
        max_score=Decimal("20"),
        weight=Decimal(weight),
        created_by=base_data["teacher1"],
    )


def add_enrollment(base_data, *, national_id, student_number):
    student = Student.objects.create(
        organization=base_data["organization"],
        national_id=national_id,
        first_name="دانش‌آموز جدید",
        last_name="آزمون",
        birth_date=date(2012, 2, 1),
        gender=Student.Gender.FEMALE,
    )
    return Enrollment.objects.create(
        student=student,
        school=base_data["school1"],
        academic_year=base_data["year"],
        grade_level=base_data["grade"],
        class_section=base_data["class1"],
        student_number=student_number,
        enrolled_on=date(2026, 9, 23),
    )


@pytest.mark.django_db
def test_score_workflow_and_locked_correction_are_auditable(base_data):
    assessment = make_assessment(base_data)
    scores = bulk_upsert_scores(
        assessment=assessment,
        entries=[
            {"enrollment": enrollment, "value": Decimal(value), "status": Score.Status.PRESENT}
            for enrollment, value in zip(base_data["enrollments"], ["18", "15"], strict=True)
        ],
        actor=base_data["teacher1"],
    )
    submit_assessment(assessment, base_data["teacher1"])
    approve_assessment(assessment, base_data["deputy"])
    lock_assessment(assessment, base_data["deputy"])
    corrected = correct_locked_score(
        score=scores[0],
        value=Decimal("19"),
        status=Score.Status.PRESENT,
        note="اصلاح",
        reason="خطای ورود اولیه",
        actor=base_data["deputy"],
    )
    assert corrected.value == Decimal("19")
    assert corrected.revision == 2
    assert ScoreRevision.objects.filter(score=corrected).count() == 2
    assert corrected.history.first().reason == "خطای ورود اولیه"


@pytest.mark.django_db
def test_incomplete_assessment_cannot_be_submitted(base_data):
    assessment = make_assessment(base_data)
    bulk_upsert_scores(
        assessment=assessment,
        entries=[
            {
                "enrollment": base_data["enrollments"][0],
                "value": Decimal("18"),
                "status": Score.Status.PRESENT,
            }
        ],
        actor=base_data["teacher1"],
    )
    with pytest.raises(ValidationError):
        submit_assessment(assessment, base_data["teacher1"])


@pytest.mark.django_db
def test_rejected_assessment_returns_to_teacher(base_data):
    assessment = make_assessment(base_data)
    bulk_upsert_scores(
        assessment=assessment,
        entries=[
            {"enrollment": enrollment, "value": Decimal("18"), "status": Score.Status.PRESENT}
            for enrollment in base_data["enrollments"]
        ],
        actor=base_data["teacher1"],
    )
    submit_assessment(assessment, base_data["teacher1"])
    reject_assessment(assessment, base_data["deputy"], "نیاز به کنترل دوباره")
    assessment.refresh_from_db()
    assert assessment.status == Assessment.Status.REJECTED
    assert assessment.rejection_reason == "نیاز به کنترل دوباره"


@pytest.mark.django_db
def test_weighted_average_and_dense_class_rank(base_data):
    continuous = make_assessment(base_data, title="مستمر", weight="1")
    final = make_assessment(
        base_data, title="پایانی", assessment_type=base_data["final"], weight="2"
    )
    final.assessment_date = date(2026, 12, 20)
    final.save(update_fields=["assessment_date"])
    for assessment, values in [(continuous, ["18", "15"]), (final, ["15", "15"])]:
        bulk_upsert_scores(
            assessment=assessment,
            entries=[
                {"enrollment": enrollment, "value": Decimal(value), "status": Score.Status.PRESENT}
                for enrollment, value in zip(base_data["enrollments"], values, strict=True)
            ],
            actor=base_data["teacher1"],
        )
        assessment.status = Assessment.Status.LOCKED
        assessment.save(update_fields=["status"])

    recalculate_class_term(base_data["class1"], base_data["term"])
    results = list(TermResult.objects.filter(term=base_data["term"]).order_by("class_rank"))
    assert results[0].average == Decimal("16.00")
    assert results[0].class_rank == 1
    assert results[1].average == Decimal("15.00")
    assert results[1].class_rank == 2


@pytest.mark.django_db
def test_unexcused_absence_is_zero_by_policy(base_data):
    assessment = make_assessment(base_data)
    bulk_upsert_scores(
        assessment=assessment,
        entries=[
            {
                "enrollment": base_data["enrollments"][0],
                "value": None,
                "status": Score.Status.UNEXCUSED_ABSENT,
            },
            {
                "enrollment": base_data["enrollments"][1],
                "value": Decimal("10"),
                "status": Score.Status.PRESENT,
            },
        ],
        actor=base_data["teacher1"],
    )
    assessment.status = Assessment.Status.LOCKED
    assessment.save(update_fields=["status"])
    recalculate_class_term(base_data["class1"], base_data["term"])
    first = TermResult.objects.get(enrollment=base_data["enrollments"][0])
    assert first.average == Decimal("0.00")


@pytest.mark.django_db
def test_submit_requires_exact_current_active_enrollment_set(base_data):
    assessment = make_assessment(base_data)
    bulk_upsert_scores(
        assessment=assessment,
        entries=[
            {"enrollment": enrollment, "value": Decimal("18"), "status": Score.Status.PRESENT}
            for enrollment in base_data["enrollments"]
        ],
        actor=base_data["teacher1"],
    )
    departed = base_data["enrollments"][1]
    departed.status = Enrollment.Status.WITHDRAWN
    departed.left_on = assessment.assessment_date - timedelta(days=1)
    departed.save(update_fields=["status", "left_on"])
    add_enrollment(base_data, national_id="0012345688", student_number="103")

    with pytest.raises(ValidationError) as exc_info:
        submit_assessment(assessment, base_data["teacher1"])

    assert "فاقد نمره: 1" in str(exc_info.value.detail)
    assert "خارج از فهرست فعال: 1" in str(exc_info.value.detail)
    assessment.refresh_from_db()
    assert assessment.status == Assessment.Status.DRAFT


@pytest.mark.django_db
def test_lock_rechecks_completeness_after_enrollment_changes(base_data):
    assessment = make_assessment(base_data)
    bulk_upsert_scores(
        assessment=assessment,
        entries=[
            {"enrollment": enrollment, "value": Decimal("17"), "status": Score.Status.PRESENT}
            for enrollment in base_data["enrollments"]
        ],
        actor=base_data["teacher1"],
    )
    submit_assessment(assessment, base_data["teacher1"])
    approve_assessment(assessment, base_data["deputy"])
    departed = base_data["enrollments"][1]
    departed.status = Enrollment.Status.WITHDRAWN
    departed.left_on = date(2026, 10, 11)
    departed.save(update_fields=["status", "left_on"])
    add_enrollment(base_data, national_id="0012345687", student_number="104")

    with pytest.raises(ValidationError):
        lock_assessment(assessment, base_data["deputy"])

    assessment.refresh_from_db()
    assert assessment.status == Assessment.Status.APPROVED


@pytest.mark.django_db
def test_dense_rank_does_not_skip_rank_after_tie(base_data):
    third = add_enrollment(base_data, national_id="0012345686", student_number="105")
    assessment = make_assessment(base_data)
    bulk_upsert_scores(
        assessment=assessment,
        entries=[
            {
                "enrollment": enrollment,
                "value": Decimal(value),
                "status": Score.Status.PRESENT,
            }
            for enrollment, value in zip(
                [*base_data["enrollments"], third], ["20", "20", "10"], strict=True
            )
        ],
        actor=base_data["teacher1"],
    )
    assessment.status = Assessment.Status.LOCKED
    assessment.save(update_fields=["status"])

    recalculate_class_term(base_data["class1"], base_data["term"])

    ranks = list(
        TermResult.objects.filter(term=base_data["term"])
        .order_by("-average", "enrollment_id")
        .values_list("class_rank", flat=True)
    )
    assert ranks == [1, 1, 2]


@pytest.mark.django_db
def test_scores_cannot_be_added_for_inactive_enrollment(base_data):
    assessment = make_assessment(base_data)
    enrollment = base_data["enrollments"][0]
    enrollment.status = Enrollment.Status.WITHDRAWN
    enrollment.left_on = assessment.assessment_date - timedelta(days=1)
    enrollment.save(update_fields=["status", "left_on"])

    with pytest.raises(ValidationError):
        bulk_upsert_scores(
            assessment=assessment,
            entries=[
                {
                    "enrollment": enrollment,
                    "value": Decimal("18"),
                    "status": Score.Status.PRESENT,
                }
            ],
            actor=base_data["teacher1"],
        )


@pytest.mark.django_db
def test_policy_precedence_rounding_and_excused_absence(base_data):
    CalculationPolicy.objects.create(
        organization=base_data["organization"],
        academic_year=base_data["year"],
        grade_level=base_data["grade"],
        version="grade-year-v2",
        title="سیاست دقیق",
        decimal_places=1,
        rounding_mode=CalculationPolicy.RoundingMode.DOWN,
        unexcused_absence_as_zero=False,
    )
    enrollment = base_data["enrollments"][0]
    policy = get_policy(enrollment)
    assert policy.version == "grade-year-v2"
    assert quantize(Decimal("12.39"), policy) == Decimal("12.3")

    assessment = make_assessment(base_data)
    score = Score(
        assessment=assessment,
        enrollment=enrollment,
        status=Score.Status.UNEXCUSED_ABSENT,
        recorded_by=base_data["teacher1"],
    )
    assert normalized_score(score, policy) is None
