from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from hamamooz.apps.academics.models import (
    AssessmentType,
    CalculationPolicy,
    CourseOffering,
    GradeSubject,
    Subject,
)
from hamamooz.apps.accounts.models import Role, RoleAssignment, User
from hamamooz.apps.organizations.models import (
    AcademicYear,
    ClassSection,
    GradeLevel,
    Organization,
    School,
    Term,
)
from hamamooz.apps.students.models import Enrollment, Student


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def base_data(db):
    organization = Organization.objects.create(name="هم‌آموز", code="hamamooz")
    school1 = School.objects.create(organization=organization, code="s1", name="شعبه یک")
    school2 = School.objects.create(organization=organization, code="s2", name="شعبه دو")
    year = AcademicYear.objects.create(
        organization=organization,
        code="1405-1406",
        title="۱۴۰۵-۱۴۰۶",
        starts_on=date(2026, 9, 23),
        ends_on=date(2027, 6, 22),
        is_current=True,
    )
    term = Term.objects.create(
        academic_year=year,
        code=Term.Code.FIRST,
        title="نوبت اول",
        starts_on=date(2026, 9, 23),
        ends_on=date(2027, 1, 20),
        order=1,
    )
    grade = GradeLevel.objects.create(
        organization=organization, code="grade-7", title="هفتم", order=7
    )
    class1 = ClassSection.objects.create(
        school=school1,
        academic_year=year,
        grade_level=grade,
        code="7-a",
        title="هفتم الف",
        capacity=35,
    )
    class2 = ClassSection.objects.create(
        school=school2,
        academic_year=year,
        grade_level=grade,
        code="7-b",
        title="هفتم ب",
        capacity=35,
    )

    manager = User.objects.create_user(
        username="manager", email="manager@example.com", password="Strong-pass-123"
    )
    deputy = User.objects.create_user(
        username="deputy", email="deputy@example.com", password="Strong-pass-123"
    )
    teacher1 = User.objects.create_user(
        username="teacher1", email="teacher1@example.com", password="Strong-pass-123"
    )
    teacher2 = User.objects.create_user(
        username="teacher2", email="teacher2@example.com", password="Strong-pass-123"
    )
    for user, role, school in [
        (manager, Role.SCHOOL_MANAGER, school1),
        (deputy, Role.EDUCATIONAL_DEPUTY, school1),
        (teacher1, Role.TEACHER, school1),
        (teacher2, Role.TEACHER, school2),
    ]:
        RoleAssignment.objects.create(
            user=user, organization=organization, school=school, role=role
        )

    subject = Subject.objects.create(
        organization=organization,
        code="math",
        title="ریاضی",
        default_coefficient=Decimal("2"),
    )
    grade_subject = GradeSubject.objects.create(
        grade_level=grade,
        subject=subject,
        coefficient=Decimal("2"),
        pass_mark=Decimal("10"),
    )
    offering1 = CourseOffering.objects.create(
        class_section=class1, grade_subject=grade_subject, term=term, teacher=teacher1
    )
    offering2 = CourseOffering.objects.create(
        class_section=class2, grade_subject=grade_subject, term=term, teacher=teacher2
    )
    continuous = AssessmentType.objects.create(
        organization=organization,
        code="continuous",
        title="مستمر",
        category=AssessmentType.Category.CONTINUOUS,
        default_weight=Decimal("1"),
    )
    final = AssessmentType.objects.create(
        organization=organization,
        code="final",
        title="پایانی",
        category=AssessmentType.Category.FINAL,
        default_weight=Decimal("2"),
    )
    CalculationPolicy.objects.create(
        organization=organization,
        academic_year=year,
        version="mvp-v1",
        title="استاندارد",
    )

    students = []
    enrollments = []
    for index, national_id in enumerate(["0012345678", "0012345679"], start=1):
        student = Student.objects.create(
            organization=organization,
            national_id=national_id,
            first_name=f"دانش‌آموز {index}",
            last_name="آزمون",
            birth_date=date(2012, 1, index),
            gender=Student.Gender.MALE,
        )
        enrollment = Enrollment.objects.create(
            student=student,
            school=school1,
            academic_year=year,
            grade_level=grade,
            class_section=class1,
            student_number=f"10{index}",
            enrolled_on=date(2026, 9, 23),
        )
        students.append(student)
        enrollments.append(enrollment)

    return {
        "organization": organization,
        "school1": school1,
        "school2": school2,
        "year": year,
        "term": term,
        "grade": grade,
        "class1": class1,
        "class2": class2,
        "manager": manager,
        "deputy": deputy,
        "teacher1": teacher1,
        "teacher2": teacher2,
        "subject": subject,
        "grade_subject": grade_subject,
        "offering1": offering1,
        "offering2": offering2,
        "continuous": continuous,
        "final": final,
        "students": students,
        "enrollments": enrollments,
    }
