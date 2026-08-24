from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from hamamooz.apps.academics.models import Subject
from hamamooz.apps.accounts.models import Role, RoleAssignment, User
from hamamooz.apps.core.models import AuditEvent
from hamamooz.apps.summers.models import (
    SummerComprehensiveExam,
    SummerCourse,
    SummerCourseRegistration,
    SummerProgram,
    SummerProgramRevision,
    SummerRegistration,
    SummerSubjectScore,
)
from hamamooz.apps.summers.services import (
    summer_registration_result,
    validate_summer_report_readiness,
)
from hamamooz.apps.summers.views import (
    SummerComprehensiveExamViewSet,
    SummerProgramViewSet,
    SummerRegistrationViewSet,
    SummerSubjectScoreViewSet,
)


def summer_records(base_data, *, threshold=Decimal("10"), status="finalized"):
    program = SummerProgram.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        title="تابستان ۱۴۰۶",
        pass_threshold=threshold,
    )
    course = SummerCourse.objects.create(program=program, subject=base_data["subject"])
    registration = SummerRegistration.objects.create(
        program=program,
        enrollment=base_data["enrollments"][0],
    )
    course_registration = SummerCourseRegistration.objects.create(
        registration=registration,
        course=course,
    )
    exam = SummerComprehensiveExam.objects.create(
        program=program,
        title="آزمون جامع",
        exam_date=date(2027, 6, 20),
        status=status,
        finalized_at=timezone.now() if status == "finalized" else None,
        finalized_by=base_data["deputy"] if status == "finalized" else None,
    )
    return program, registration, course_registration, exam


@pytest.mark.django_db
def test_summer_result_uses_direct_decimal_scores_and_optional_threshold(base_data):
    program, registration, course_registration, exam = summer_records(
        base_data, threshold=None
    )
    SummerSubjectScore.objects.create(
        exam=exam,
        course_registration=course_registration,
        value=Decimal("13.25"),
        recorded_by=base_data["deputy"],
    )

    result = summer_registration_result(registration)

    assert result["average"] == Decimal("13.25")
    assert result["pass_threshold"] is None
    assert result["passed"] is None
    assert result["courses"] == [
        {
            "course_registration_id": str(course_registration.id),
            "subject_id": str(base_data["subject"].id),
            "subject_title": "ریاضی",
            "coefficient": Decimal("2"),
            "score": Decimal("13.25"),
        }
    ]


@pytest.mark.django_db
def test_summer_result_applies_subject_coefficients_and_program_threshold(base_data):
    program, registration, first_course_registration, exam = summer_records(
        base_data, threshold=Decimal("14")
    )
    science = Subject.objects.create(
        organization=base_data["organization"],
        code="science-summer",
        title="علوم",
        default_coefficient=Decimal("1"),
    )
    science_course = SummerCourse.objects.create(program=program, subject=science)
    second_course_registration = SummerCourseRegistration.objects.create(
        registration=registration,
        course=science_course,
    )
    SummerSubjectScore.objects.bulk_create(
        [
            SummerSubjectScore(
                exam=exam,
                course_registration=first_course_registration,
                value=Decimal("12"),
                recorded_by=base_data["deputy"],
            ),
            SummerSubjectScore(
                exam=exam,
                course_registration=second_course_registration,
                value=Decimal("18"),
                recorded_by=base_data["deputy"],
            ),
        ]
    )

    result = summer_registration_result(registration, exam)

    assert result["average"] == Decimal("14.00")
    assert result["pass_threshold"] == Decimal("14")
    assert result["passed"] is True


@pytest.mark.django_db
@pytest.mark.parametrize("value", [Decimal("0"), Decimal("20")])
def test_summer_score_accepts_inclusive_boundaries(base_data, value):
    _, _, course_registration, exam = summer_records(base_data)
    score = SummerSubjectScore(
        exam=exam,
        course_registration=course_registration,
        value=value,
        recorded_by=base_data["deputy"],
    )

    score.full_clean()
    score.save()

    assert score.value == value


@pytest.mark.django_db
@pytest.mark.parametrize("value", [Decimal("-0.01"), Decimal("20.01")])
def test_summer_score_rejects_values_outside_twenty_point_scale(base_data, value):
    _, _, course_registration, exam = summer_records(base_data)
    score = SummerSubjectScore(
        exam=exam,
        course_registration=course_registration,
        value=value,
        recorded_by=base_data["deputy"],
    )

    with pytest.raises(DjangoValidationError):
        score.full_clean()


@pytest.mark.django_db
def test_summer_threshold_accepts_null_zero_twenty_and_rejects_out_of_range(base_data):
    for threshold in [None, Decimal("0"), Decimal("20")]:
        program = SummerProgram(
            school=base_data["school1"],
            academic_year=base_data["year"],
            title=f"تابستان {threshold}",
            pass_threshold=threshold,
        )
        program.full_clean(validate_unique=False, validate_constraints=False)

    for threshold in [Decimal("-0.01"), Decimal("20.01")]:
        program = SummerProgram(
            school=base_data["school1"],
            academic_year=base_data["year"],
            title="نامعتبر",
            pass_threshold=threshold,
        )
        with pytest.raises(DjangoValidationError):
            program.full_clean(validate_unique=False, validate_constraints=False)


@pytest.mark.django_db
def test_summer_score_is_unique_per_exam_and_registered_course(base_data):
    _, _, course_registration, exam = summer_records(base_data)
    SummerSubjectScore.objects.create(
        exam=exam,
        course_registration=course_registration,
        value=Decimal("10"),
        recorded_by=base_data["deputy"],
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        SummerSubjectScore.objects.create(
            exam=exam,
            course_registration=course_registration,
            value=Decimal("11"),
            recorded_by=base_data["deputy"],
        )


@pytest.mark.django_db
def test_summer_course_registration_and_exam_are_unique_in_program(base_data):
    program, registration, course_registration, exam = summer_records(base_data)

    with pytest.raises(IntegrityError), transaction.atomic():
        SummerCourseRegistration.objects.create(
            registration=registration,
            course=course_registration.course,
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        SummerComprehensiveExam.objects.create(
            program=program,
            title="آزمون تکراری",
            exam_date=exam.exam_date,
        )


@pytest.mark.django_db
def test_summer_registration_requires_matching_enrollment_school_and_year(base_data):
    program = SummerProgram.objects.create(
        school=base_data["school2"],
        academic_year=base_data["year"],
        title="تابستان شعبه دوم",
    )
    registration = SummerRegistration(
        program=program,
        enrollment=base_data["enrollments"][0],
    )

    with pytest.raises(DjangoValidationError):
        registration.full_clean()


@pytest.mark.django_db
def test_cross_program_exam_score_is_rejected(base_data):
    _, _, course_registration, _ = summer_records(base_data)
    other_program = SummerProgram.objects.create(
        school=base_data["school2"],
        academic_year=base_data["year"],
        title="تابستان شعبه دوم",
    )
    other_exam = SummerComprehensiveExam.objects.create(
        program=other_program,
        title="جامع شعبه دوم",
        exam_date=date(2027, 6, 20),
    )
    score = SummerSubjectScore(
        exam=other_exam,
        course_registration=course_registration,
        value=Decimal("15"),
        recorded_by=base_data["deputy"],
    )

    with pytest.raises(DjangoValidationError):
        score.full_clean()


@pytest.mark.django_db
def test_summer_report_readiness_rejects_draft_exam_and_missing_score(base_data):
    _, registration, course_registration, exam = summer_records(base_data, status="draft")
    SummerSubjectScore.objects.create(
        exam=exam,
        course_registration=course_registration,
        value=Decimal("16"),
        recorded_by=base_data["deputy"],
    )

    with pytest.raises(ValidationError, match="نهایی"):
        validate_summer_report_readiness(registration, exam)

    exam.status = SummerComprehensiveExam.Status.FINALIZED
    exam.finalized_at = timezone.now()
    exam.finalized_by = base_data["deputy"]
    exam.save(update_fields=["status", "finalized_at", "finalized_by", "updated_at"])
    SummerSubjectScore.objects.all().delete()

    with pytest.raises(ValidationError, match="ناقص"):
        validate_summer_report_readiness(registration, exam)


@pytest.mark.django_db
def test_threshold_update_requires_reason_and_creates_revision_and_public_audit(base_data):
    program = SummerProgram.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        title="تابستان ۱۴۰۶",
        pass_threshold=Decimal("10"),
    )
    factory = APIRequestFactory()
    view = SummerProgramViewSet.as_view({"patch": "partial_update"})

    missing_reason = factory.patch(
        f"/summer-programs/{program.id}/",
        {"pass_threshold": "12"},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    force_authenticate(missing_reason, base_data["deputy"])
    assert view(missing_reason, pk=program.id).status_code == 400

    request = factory.patch(
        f"/summer-programs/{program.id}/",
        {"pass_threshold": "12", "threshold_change_reason": "مصوبه شورای آموزشی"},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    force_authenticate(request, base_data["deputy"])

    response = view(request, pk=program.id)

    assert response.status_code == 200
    revision = SummerProgramRevision.objects.get(program=program)
    assert revision.actor == base_data["deputy"]
    assert revision.old_pass_threshold == Decimal("10")
    assert revision.new_pass_threshold == Decimal("12")
    assert revision.reason == "مصوبه شورای آموزشی"
    assert AuditEvent.objects.filter(
        entity_id=str(program.id), school_id=base_data["school1"].id, action="update"
    ).exists()


@pytest.mark.django_db
def test_summer_program_list_is_school_scoped(base_data):
    own = SummerProgram.objects.create(
        school=base_data["school1"], academic_year=base_data["year"], title="شعبه یک"
    )
    SummerProgram.objects.create(
        school=base_data["school2"], academic_year=base_data["year"], title="شعبه دو"
    )
    factory = APIRequestFactory()
    request = factory.get(
        "/summer-programs/", HTTP_X_SCHOOL_ID=str(base_data["school1"].id)
    )
    force_authenticate(request, base_data["manager"])

    response = SummerProgramViewSet.as_view({"get": "list"})(request)

    assert response.status_code == 200
    assert [item["id"] for item in response.data["results"]] == [str(own.id)]


@pytest.mark.django_db
def test_teacher_cannot_write_summer_score_and_cannot_read_student_scores(base_data):
    _, _, course_registration, exam = summer_records(base_data, status="draft")
    SummerSubjectScore.objects.create(
        exam=exam,
        course_registration=course_registration,
        value=Decimal("17"),
        recorded_by=base_data["deputy"],
    )
    factory = APIRequestFactory()
    list_request = factory.get(
        "/summer-subject-scores/", HTTP_X_SCHOOL_ID=str(base_data["school1"].id)
    )
    force_authenticate(list_request, base_data["teacher1"])
    listed = SummerSubjectScoreViewSet.as_view({"get": "list"})(list_request)

    create_request = factory.post(
        "/summer-subject-scores/",
        {
            "exam": str(exam.id),
            "course_registration": str(course_registration.id),
            "value": "18",
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    force_authenticate(create_request, base_data["teacher1"])
    created = SummerSubjectScoreViewSet.as_view({"post": "create"})(create_request)

    assert listed.status_code == 200
    assert listed.data["results"] == []
    assert created.status_code == 403


@pytest.mark.django_db
def test_manager_finalizes_only_a_complete_comprehensive_exam(base_data):
    _, _, course_registration, exam = summer_records(base_data, status="draft")
    SummerSubjectScore.objects.create(
        exam=exam,
        course_registration=course_registration,
        value=Decimal("17"),
        recorded_by=base_data["deputy"],
    )
    factory = APIRequestFactory()
    request = factory.post(
        f"/summer-exams/{exam.id}/finalize/",
        {},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    force_authenticate(request, base_data["manager"])

    response = SummerComprehensiveExamViewSet.as_view({"post": "finalize"})(
        request, pk=exam.id
    )

    assert response.status_code == 200
    exam.refresh_from_db()
    assert exam.status == SummerComprehensiveExam.Status.FINALIZED
    assert exam.finalized_by == base_data["manager"]
    assert exam.finalized_at is not None
    assert AuditEvent.objects.filter(
        action="summer_exam.finalized",
        entity_id=str(exam.id),
        school_id=base_data["school1"].id,
    ).exists()


@pytest.mark.django_db
def test_finalized_comprehensive_exam_rejects_new_program_registrations(base_data):
    program, _, _, _ = summer_records(base_data, status="finalized")
    factory = APIRequestFactory()
    request = factory.post(
        "/summer-registrations/",
        {
            "program": str(program.id),
            "enrollment": str(base_data["enrollments"][1].id),
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    force_authenticate(request, base_data["manager"])

    response = SummerRegistrationViewSet.as_view({"post": "create"})(request)

    assert response.status_code == 403
    assert program.registrations.count() == 1


@pytest.mark.django_db
def test_operator_may_enter_score_but_cannot_finalize_exam(base_data):
    operator = User.objects.create_user(
        username="summer-operator",
        email="summer-operator@example.com",
        password="Strong-pass-123",
    )
    RoleAssignment.objects.create(
        user=operator,
        organization=base_data["organization"],
        school=base_data["school1"],
        role=Role.OPERATOR,
    )
    _, _, course_registration, exam = summer_records(base_data, status="draft")
    factory = APIRequestFactory()
    request = factory.post(
        "/summer-subject-scores/",
        {
            "exam": str(exam.id),
            "course_registration": str(course_registration.id),
            "value": "19",
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    force_authenticate(request, operator)

    response = SummerSubjectScoreViewSet.as_view({"post": "create"})(request)

    finalize_request = factory.post(
        f"/summer-exams/{exam.id}/finalize/",
        {},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    force_authenticate(finalize_request, operator)
    finalized = SummerComprehensiveExamViewSet.as_view({"post": "finalize"})(
        finalize_request, pk=exam.id
    )

    assert response.status_code == 201
    assert SummerSubjectScore.objects.get().recorded_by == operator
    assert finalized.status_code == 403


@pytest.mark.django_db
def test_duplicate_summer_score_is_a_validation_error_and_preserves_original(base_data):
    _, _, course_registration, exam = summer_records(base_data, status="draft")
    SummerSubjectScore.objects.create(
        exam=exam,
        course_registration=course_registration,
        value=Decimal("14"),
        recorded_by=base_data["deputy"],
    )
    request = APIRequestFactory().post(
        "/summer-subject-scores/",
        {
            "exam": str(exam.id),
            "course_registration": str(course_registration.id),
            "value": "19",
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    force_authenticate(request, base_data["deputy"])

    response = SummerSubjectScoreViewSet.as_view({"post": "create"})(request)

    assert response.status_code == 400
    assert SummerSubjectScore.objects.get(exam=exam).value == Decimal("14")
