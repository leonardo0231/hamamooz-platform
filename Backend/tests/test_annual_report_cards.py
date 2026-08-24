from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework.test import APIRequestFactory, force_authenticate

from hamamooz.apps.academics.calculations import (
    calculate_enrollment_annual,
    get_academic_report_settings,
    recalculate_school_annual,
)
from hamamooz.apps.academics.models import (
    AcademicReportSettings,
    AcademicReportSettingsRevision,
    AnnualResult,
    AnnualSubjectResult,
    CourseOffering,
    GradeSubject,
    Subject,
    SubjectResult,
)
from hamamooz.apps.academics.views import AcademicReportSettingsViewSet
from hamamooz.apps.accounts.models import Role, RoleAssignment, User
from hamamooz.apps.core.models import AuditEvent
from hamamooz.apps.organizations.models import ClassSection, GradeLevel, Term
from hamamooz.apps.students.models import Enrollment, Student


def make_second_term(base_data):
    return Term.objects.create(
        academic_year=base_data["year"],
        code=Term.Code.SECOND,
        title="نوبت دوم",
        starts_on=date(2027, 1, 21),
        ends_on=date(2027, 6, 22),
        order=2,
    )


def make_offering(base_data, *, class_section, grade_subject, term):
    return CourseOffering.objects.create(
        class_section=class_section,
        grade_subject=grade_subject,
        term=term,
        teacher=base_data["teacher1"],
    )


def make_student_enrollment(
    base_data,
    *,
    national_id,
    student_number,
    class_section=None,
    grade_level=None,
):
    class_section = class_section or base_data["class1"]
    grade_level = grade_level or class_section.grade_level
    student = Student.objects.create(
        organization=base_data["organization"],
        national_id=national_id,
        first_name="دانش‌آموز",
        last_name=student_number,
        birth_date=date(2012, 3, 1),
        gender=Student.Gender.FEMALE,
    )
    return Enrollment.objects.create(
        student=student,
        school=class_section.school,
        academic_year=base_data["year"],
        grade_level=grade_level,
        class_section=class_section,
        student_number=student_number,
        enrolled_on=base_data["year"].starts_on,
    )


def add_term_subject_results(
    *, enrollment, grade_subject, first_offering, second_offering, first, second
):
    SubjectResult.objects.update_or_create(
        enrollment=enrollment,
        course_offering=first_offering,
        defaults={
            "average": Decimal(first) if first is not None else None,
            "passed": first is not None and Decimal(first) >= grade_subject.pass_mark,
            "formula_version": "test-v1",
        },
    )
    if second_offering is not None:
        SubjectResult.objects.update_or_create(
            enrollment=enrollment,
            course_offering=second_offering,
            defaults={
                "average": Decimal(second) if second is not None else None,
                "passed": second is not None and Decimal(second) >= grade_subject.pass_mark,
                "formula_version": "test-v1",
            },
        )


@pytest.mark.django_db
def test_settings_have_backward_compatible_defaults_and_reject_nonpositive_weights(base_data):
    settings = get_academic_report_settings(base_data["school1"], base_data["year"])

    assert settings.first_term_weight == Decimal("1")
    assert settings.second_term_weight == Decimal("2")
    assert settings.show_class_rank is True
    assert settings.show_grade_rank is True
    assert settings.show_school_rank is True

    invalid = AcademicReportSettings(
        school=base_data["school1"],
        academic_year=base_data["year"],
        first_term_weight=Decimal("0"),
        second_term_weight=Decimal("-1"),
    )
    with pytest.raises(DjangoValidationError):
        invalid.full_clean()


@pytest.mark.django_db
def test_settings_are_unique_per_school_year_and_validate_tenant_consistency(base_data):
    AcademicReportSettings.objects.create(
        school=base_data["school1"], academic_year=base_data["year"]
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        AcademicReportSettings.objects.create(
            school=base_data["school1"], academic_year=base_data["year"]
        )

    other_organization = base_data["organization"].__class__.objects.create(
        name="مجموعه دیگر", code="other-report-settings"
    )
    other_year = base_data["year"].__class__.objects.create(
        organization=other_organization,
        code="1405-other",
        title="سال دیگر",
        starts_on=base_data["year"].starts_on,
        ends_on=base_data["year"].ends_on,
    )
    cross_tenant = AcademicReportSettings(
        school=base_data["school1"], academic_year=other_year
    )
    with pytest.raises(DjangoValidationError):
        cross_tenant.full_clean()


@pytest.mark.django_db
def test_manager_can_revise_settings_with_actor_reason_snapshot_and_public_audit(base_data):
    settings = AcademicReportSettings.objects.create(
        school=base_data["school1"], academic_year=base_data["year"]
    )
    request = APIRequestFactory().patch(
        f"/api/v1/academic-report-settings/{settings.id}/",
        {
            "first_term_weight": "1.50",
            "second_term_weight": "2.50",
            "show_grade_rank": False,
            "reason": "مصوبه شورای آموزشی",
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    force_authenticate(request, base_data["manager"])

    response = AcademicReportSettingsViewSet.as_view({"patch": "partial_update"})(
        request, pk=settings.id
    )

    assert response.status_code == 200
    settings.refresh_from_db()
    assert settings.revision == 2
    assert settings.first_term_weight == Decimal("1.500")
    assert settings.second_term_weight == Decimal("2.500")
    assert settings.show_grade_rank is False
    revision = AcademicReportSettingsRevision.objects.get(report_settings=settings)
    assert revision.changed_by == base_data["manager"]
    assert revision.reason == "مصوبه شورای آموزشی"
    assert revision.before["first_term_weight"] == "1.000"
    assert revision.after["first_term_weight"] == "1.500"
    assert revision.before["show_grade_rank"] is True
    assert revision.after["show_grade_rank"] is False
    assert AuditEvent.objects.filter(
        action="academic_report_settings.updated", entity_id=str(settings.id)
    ).exists()


@pytest.mark.django_db
def test_operator_cannot_mutate_academic_report_settings(base_data):
    operator = User.objects.create_user(
        username="report-settings-operator",
        email="report-settings-operator@example.com",
        password="Strong-pass-123",
    )
    RoleAssignment.objects.create(
        user=operator,
        organization=base_data["organization"],
        school=base_data["school1"],
        role=Role.OPERATOR,
    )
    settings = AcademicReportSettings.objects.create(
        school=base_data["school1"], academic_year=base_data["year"]
    )
    request = APIRequestFactory().patch(
        f"/api/v1/academic-report-settings/{settings.id}/",
        {"first_term_weight": "3", "reason": "تغییر غیرمجاز"},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    force_authenticate(request, operator)

    response = AcademicReportSettingsViewSet.as_view({"patch": "partial_update"})(
        request, pk=settings.id
    )

    assert response.status_code == 403
    settings.refresh_from_db()
    assert settings.first_term_weight == Decimal("1")
    assert not settings.history.exists()


@pytest.mark.django_db
def test_annual_subject_and_overall_averages_use_term_weights_and_subject_coefficients(base_data):
    second_term = make_second_term(base_data)
    second_math = make_offering(
        base_data,
        class_section=base_data["class1"],
        grade_subject=base_data["grade_subject"],
        term=second_term,
    )
    science = Subject.objects.create(
        organization=base_data["organization"],
        code="annual-science",
        title="علوم سالانه",
        default_coefficient=Decimal("1"),
    )
    science_grade = GradeSubject.objects.create(
        grade_level=base_data["grade"],
        subject=science,
        coefficient=Decimal("1"),
        pass_mark=Decimal("10"),
    )
    first_science = make_offering(
        base_data,
        class_section=base_data["class1"],
        grade_subject=science_grade,
        term=base_data["term"],
    )
    second_science = make_offering(
        base_data,
        class_section=base_data["class1"],
        grade_subject=science_grade,
        term=second_term,
    )
    AcademicReportSettings.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        first_term_weight=Decimal("1"),
        second_term_weight=Decimal("2"),
    )
    enrollment = base_data["enrollments"][0]
    add_term_subject_results(
        enrollment=enrollment,
        grade_subject=base_data["grade_subject"],
        first_offering=base_data["offering1"],
        second_offering=second_math,
        first="15",
        second="18",
    )
    add_term_subject_results(
        enrollment=enrollment,
        grade_subject=science_grade,
        first_offering=first_science,
        second_offering=second_science,
        first="10",
        second="10",
    )

    result = calculate_enrollment_annual(enrollment)

    assert result.complete is True
    assert AnnualSubjectResult.objects.get(
        enrollment=enrollment, grade_subject=base_data["grade_subject"]
    ).average == Decimal("17.00")
    assert result.average == Decimal("14.67")


@pytest.mark.django_db
def test_annual_result_is_incomplete_when_either_required_term_is_missing(base_data):
    make_second_term(base_data)
    enrollment = base_data["enrollments"][0]
    add_term_subject_results(
        enrollment=enrollment,
        grade_subject=base_data["grade_subject"],
        first_offering=base_data["offering1"],
        second_offering=None,
        first="15",
        second=None,
    )

    result = calculate_enrollment_annual(enrollment)

    assert result.complete is False
    assert result.average is None
    subject_result = AnnualSubjectResult.objects.get(
        enrollment=enrollment, grade_subject=base_data["grade_subject"]
    )
    assert subject_result.complete is False
    assert subject_result.average is None


@pytest.mark.django_db
def test_annual_calculation_uses_historical_segments_but_persists_under_latest_active_anchor(
    base_data,
):
    second_term = make_second_term(base_data)
    historical = base_data["enrollments"][0]
    historical.status = Enrollment.Status.TRANSFERRED
    historical.left_on = base_data["term"].ends_on
    historical.save(update_fields=["status", "left_on"])
    new_class = ClassSection.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        grade_level=base_data["grade"],
        code="7-history-target",
        title="هفتم ج",
        capacity=30,
    )
    active = Enrollment.objects.create(
        student=historical.student,
        school=historical.school,
        academic_year=historical.academic_year,
        grade_level=historical.grade_level,
        class_section=new_class,
        student_number="history-target",
        enrolled_on=second_term.starts_on,
    )
    second_offering = make_offering(
        base_data,
        class_section=new_class,
        grade_subject=base_data["grade_subject"],
        term=second_term,
    )
    add_term_subject_results(
        enrollment=historical,
        grade_subject=base_data["grade_subject"],
        first_offering=base_data["offering1"],
        second_offering=None,
        first="15",
        second=None,
    )
    add_term_subject_results(
        enrollment=active,
        grade_subject=base_data["grade_subject"],
        first_offering=second_offering,
        second_offering=second_offering,
        first="18",
        second="18",
    )

    result = calculate_enrollment_annual(historical)

    assert result.enrollment == active
    assert result.average == Decimal("17.00")
    assert AnnualResult.objects.filter(enrollment=historical).count() == 0
    assert AnnualSubjectResult.objects.get(
        enrollment=active, grade_subject=base_data["grade_subject"]
    ).average == Decimal("17.00")


@pytest.mark.django_db
def test_annual_recalculation_removes_stale_result_from_pre_transfer_anchor(base_data):
    second_term = make_second_term(base_data)
    historical = base_data["enrollments"][0]
    old_second = make_offering(
        base_data,
        class_section=base_data["class1"],
        grade_subject=base_data["grade_subject"],
        term=second_term,
    )
    add_term_subject_results(
        enrollment=historical,
        grade_subject=base_data["grade_subject"],
        first_offering=base_data["offering1"],
        second_offering=old_second,
        first="15",
        second="18",
    )
    stale = calculate_enrollment_annual(historical)
    assert stale.enrollment == historical

    historical.status = Enrollment.Status.TRANSFERRED
    historical.left_on = base_data["term"].ends_on
    historical.save(update_fields=["status", "left_on"])
    new_class = ClassSection.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        grade_level=base_data["grade"],
        code="7-stale-target",
        title="هفتم انتقال",
        capacity=30,
    )
    active = Enrollment.objects.create(
        student=historical.student,
        school=historical.school,
        academic_year=historical.academic_year,
        grade_level=historical.grade_level,
        class_section=new_class,
        student_number="stale-target",
        enrolled_on=second_term.starts_on,
    )

    current = calculate_enrollment_annual(historical)

    assert current.enrollment == active
    assert not AnnualResult.objects.filter(pk=stale.pk).exists()
    assert AnnualResult.objects.filter(
        enrollment__student=historical.student,
        enrollment__school=historical.school,
        enrollment__academic_year=historical.academic_year,
        enrollment__grade_level=historical.grade_level,
    ).count() == 1


@pytest.mark.django_db
def test_required_annual_subjects_respect_enrollment_term_date_overlap(base_data):
    second_term = make_second_term(base_data)
    historical = base_data["enrollments"][0]
    historical.status = Enrollment.Status.TRANSFERRED
    historical.left_on = base_data["term"].ends_on
    historical.save(update_fields=["status", "left_on"])
    new_class = ClassSection.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        grade_level=base_data["grade"],
        code="7-overlap-target",
        title="هفتم هم‌پوشانی",
        capacity=30,
    )
    active = Enrollment.objects.create(
        student=historical.student,
        school=historical.school,
        academic_year=historical.academic_year,
        grade_level=historical.grade_level,
        class_section=new_class,
        student_number="overlap-target",
        enrolled_on=second_term.starts_on,
    )
    new_math_second = make_offering(
        base_data,
        class_section=new_class,
        grade_subject=base_data["grade_subject"],
        term=second_term,
    )
    elective = Subject.objects.create(
        organization=base_data["organization"],
        code="outside-membership-elective",
        title="درس خارج از بازه عضویت",
    )
    elective_grade = GradeSubject.objects.create(
        grade_level=base_data["grade"],
        subject=elective,
    )
    make_offering(
        base_data,
        class_section=base_data["class1"],
        grade_subject=elective_grade,
        term=second_term,
    )
    make_offering(
        base_data,
        class_section=new_class,
        grade_subject=elective_grade,
        term=base_data["term"],
    )
    add_term_subject_results(
        enrollment=historical,
        grade_subject=base_data["grade_subject"],
        first_offering=base_data["offering1"],
        second_offering=None,
        first="15",
        second=None,
    )
    add_term_subject_results(
        enrollment=active,
        grade_subject=base_data["grade_subject"],
        first_offering=new_math_second,
        second_offering=new_math_second,
        first="18",
        second="18",
    )

    result = calculate_enrollment_annual(active)

    assert result.complete is True
    assert result.average == Decimal("17.00")
    assert not result.subject_results.filter(grade_subject=elective_grade).exists()


@pytest.mark.django_db
def test_annual_dense_ranks_and_populations_are_scoped_to_active_class_grade_and_school(
    base_data,
):
    second_term = make_second_term(base_data)
    second_class = ClassSection.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        grade_level=base_data["grade"],
        code="7-rank-b",
        title="هفتم ب",
        capacity=30,
    )
    second_class_first = make_offering(
        base_data,
        class_section=second_class,
        grade_subject=base_data["grade_subject"],
        term=base_data["term"],
    )
    second_class_second = make_offering(
        base_data,
        class_section=second_class,
        grade_subject=base_data["grade_subject"],
        term=second_term,
    )
    first_class_second = make_offering(
        base_data,
        class_section=base_data["class1"],
        grade_subject=base_data["grade_subject"],
        term=second_term,
    )
    third = make_student_enrollment(
        base_data,
        national_id="0012345601",
        student_number="rank-third",
        class_section=second_class,
    )

    grade8 = GradeLevel.objects.create(
        organization=base_data["organization"], code="annual-grade-8", title="هشتم", order=8
    )
    class8 = ClassSection.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        grade_level=grade8,
        code="8-rank-a",
        title="هشتم الف",
        capacity=30,
    )
    grade8_subject = GradeSubject.objects.create(
        grade_level=grade8,
        subject=base_data["subject"],
        coefficient=Decimal("2"),
        pass_mark=Decimal("10"),
    )
    grade8_first = make_offering(
        base_data,
        class_section=class8,
        grade_subject=grade8_subject,
        term=base_data["term"],
    )
    grade8_second = make_offering(
        base_data,
        class_section=class8,
        grade_subject=grade8_subject,
        term=second_term,
    )
    fourth = make_student_enrollment(
        base_data,
        national_id="0012345602",
        student_number="rank-fourth",
        class_section=class8,
        grade_level=grade8,
    )

    for enrollment, first_offering, second_offering, value in [
        (base_data["enrollments"][0], base_data["offering1"], first_class_second, "18"),
        (base_data["enrollments"][1], base_data["offering1"], first_class_second, "18"),
        (third, second_class_first, second_class_second, "10"),
        (fourth, grade8_first, grade8_second, "12"),
    ]:
        grade_subject = first_offering.grade_subject
        add_term_subject_results(
            enrollment=enrollment,
            grade_subject=grade_subject,
            first_offering=first_offering,
            second_offering=second_offering,
            first=value,
            second=value,
        )

    results = recalculate_school_annual(base_data["school1"], base_data["year"])
    by_enrollment = {result.enrollment_id: result for result in results}

    first = by_enrollment[base_data["enrollments"][0].id]
    second = by_enrollment[base_data["enrollments"][1].id]
    low = by_enrollment[third.id]
    other_grade = by_enrollment[fourth.id]
    assert (first.class_rank, second.class_rank) == (1, 1)
    assert low.class_rank == 1
    assert (first.grade_rank, second.grade_rank, low.grade_rank) == (1, 1, 2)
    assert (first.school_rank, second.school_rank, other_grade.school_rank, low.school_rank) == (
        1,
        1,
        2,
        3,
    )
    assert first.class_population == 2
    assert first.grade_population == 3
    assert first.school_population == 4
    assert other_grade.grade_population == 1


@pytest.mark.django_db
def test_transferred_out_student_is_calculated_but_excluded_from_annual_ranks(base_data):
    second_term = make_second_term(base_data)
    second_offering = make_offering(
        base_data,
        class_section=base_data["class1"],
        grade_subject=base_data["grade_subject"],
        term=second_term,
    )
    transferred = base_data["enrollments"][0]
    transferred.status = Enrollment.Status.TRANSFERRED
    transferred.left_on = second_term.ends_on
    transferred.save(update_fields=["status", "left_on"])
    add_term_subject_results(
        enrollment=transferred,
        grade_subject=base_data["grade_subject"],
        first_offering=base_data["offering1"],
        second_offering=second_offering,
        first="20",
        second="20",
    )

    direct = calculate_enrollment_annual(transferred)
    ranked = recalculate_school_annual(base_data["school1"], base_data["year"])

    assert direct.average == Decimal("20.00")
    direct.refresh_from_db()
    assert direct.class_rank is None
    assert direct.grade_rank is None
    assert direct.school_rank is None
    assert transferred.id not in {result.enrollment_id for result in ranked}
