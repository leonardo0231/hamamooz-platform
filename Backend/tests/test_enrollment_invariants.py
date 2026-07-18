from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from django.db import close_old_connections, connection
from rest_framework.exceptions import ValidationError

from hamamooz.apps.organizations.models import ClassSection
from hamamooz.apps.students.models import Enrollment, Student
from hamamooz.apps.students.services import (
    change_class,
    change_status,
    create_enrollment,
    transfer_enrollment,
)


def make_student(base_data, national_id):
    return Student.objects.create(
        organization=base_data["organization"],
        national_id=national_id,
        first_name="ظرفیت",
        last_name="آزمون",
        birth_date=date(2012, 5, 1),
        gender=Student.Gender.MALE,
    )


def make_enrollment(base_data, student, class_section, student_number):
    return Enrollment.objects.create(
        student=student,
        school=class_section.school,
        academic_year=base_data["year"],
        grade_level=base_data["grade"],
        class_section=class_section,
        student_number=student_number,
        enrolled_on=date(2026, 9, 23),
    )


@pytest.mark.django_db
def test_change_status_rejects_date_before_enrollment(base_data):
    enrollment = base_data["enrollments"][0]

    with pytest.raises(ValidationError):
        change_status(
            enrollment=enrollment,
            new_status=Enrollment.Status.WITHDRAWN,
            date=date(2026, 9, 22),
            reason="تاریخ اشتباه",
            actor=base_data["manager"],
        )

    enrollment.refresh_from_db()
    assert enrollment.status == Enrollment.Status.ACTIVE
    assert enrollment.left_on is None


@pytest.mark.django_db
def test_transfer_rejects_date_before_enrollment(base_data):
    enrollment = base_data["enrollments"][0]

    with pytest.raises(ValidationError):
        transfer_enrollment(
            enrollment=enrollment,
            school=base_data["school2"],
            grade_level=base_data["grade"],
            class_section=base_data["class2"],
            student_number="201",
            transfer_date=date(2026, 9, 22),
            reason="تاریخ اشتباه",
            actor=base_data["manager"],
        )

    enrollment.refresh_from_db()
    assert enrollment.status == Enrollment.Status.ACTIVE


@pytest.mark.django_db
def test_change_class_rejects_same_or_full_destination(base_data):
    enrollment = base_data["enrollments"][0]
    with pytest.raises(ValidationError):
        change_class(
            enrollment=enrollment,
            new_class=base_data["class1"],
            reason="بدون تغییر",
            actor=base_data["manager"],
        )

    full_class = ClassSection.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        grade_level=base_data["grade"],
        code="7-full",
        title="هفتم تکمیل",
        capacity=1,
    )
    occupant = make_student(base_data, "0012345685")
    make_enrollment(base_data, occupant, full_class, "full-1")

    with pytest.raises(ValidationError):
        change_class(
            enrollment=enrollment,
            new_class=full_class,
            reason="کلاس مقصد",
            actor=base_data["manager"],
        )

    enrollment.refresh_from_db()
    assert enrollment.class_section_id == base_data["class1"].id


@pytest.mark.django_db
def test_student_can_transfer_back_to_previous_school_with_history_preserved(base_data):
    original = base_data["enrollments"][0]
    second = transfer_enrollment(
        enrollment=original,
        school=base_data["school2"],
        grade_level=base_data["grade"],
        class_section=base_data["class2"],
        student_number="transfer-2",
        transfer_date=date(2026, 10, 1),
        reason="انتقال اول",
        actor=base_data["manager"],
    )
    returned = transfer_enrollment(
        enrollment=second,
        school=base_data["school1"],
        grade_level=base_data["grade"],
        class_section=base_data["class1"],
        student_number="transfer-return",
        transfer_date=date(2026, 11, 1),
        reason="بازگشت",
        actor=base_data["manager"],
    )

    history = Enrollment.objects.filter(
        student=original.student, academic_year=base_data["year"]
    ).order_by("enrolled_on")
    assert history.count() == 3
    assert returned.status == Enrollment.Status.ACTIVE
    assert list(history.values_list("school_id", flat=True)) == [
        base_data["school1"].id,
        base_data["school2"].id,
        base_data["school1"].id,
    ]


@pytest.mark.django_db
def test_class_capacity_cannot_be_reduced_below_active_enrollments(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])

    response = api_client.patch(
        f"/api/v1/classes/{base_data['class1'].id}/",
        {"capacity": 1},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 400
    base_data["class1"].refresh_from_db()
    assert base_data["class1"].capacity == 35


@pytest.mark.django_db
def test_transfer_api_requires_write_role_in_destination(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])
    enrollment = base_data["enrollments"][0]
    response = api_client.post(
        f"/api/v1/enrollments/{enrollment.id}/transfer/",
        {
            "school": str(base_data["school2"].id),
            "grade_level": str(base_data["grade"].id),
            "class_section": str(base_data["class2"].id),
            "student_number": "target-1",
            "transfer_date": "2026-10-01",
            "reason": "انتقال شعبه",
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code in {400, 403}
    enrollment.refresh_from_db()
    assert enrollment.status == Enrollment.Status.ACTIVE


@pytest.mark.django_db(transaction=True)
def test_concurrent_enrollments_cannot_overbook_a_class(base_data):
    if connection.vendor != "postgresql":
        pytest.skip("The row-lock concurrency invariant is exercised on PostgreSQL CI.")

    class_section = base_data["class1"]
    class_section.capacity = 3
    class_section.save(update_fields=["capacity"])
    student_ids = [
        make_student(base_data, national_id).id for national_id in ["0012345686", "0012345687"]
    ]
    class_id = class_section.id
    school_id = base_data["school1"].id
    year_id = base_data["year"].id
    grade_id = base_data["grade"].id

    def enroll(student_id, student_number):
        close_old_connections()
        try:
            create_enrollment(
                student=Student.objects.get(id=student_id),
                school_id=school_id,
                academic_year_id=year_id,
                grade_level_id=grade_id,
                class_section=ClassSection.objects.get(id=class_id),
                student_number=student_number,
                enrolled_on=date(2026, 9, 23),
            )
            return "created"
        except ValidationError:
            return "full"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(
                lambda args: enroll(*args),
                zip(student_ids, ["concurrent-1", "concurrent-2"], strict=True),
            )
        )

    assert sorted(outcomes) == ["created", "full"]
    assert (
        Enrollment.objects.filter(
            class_section_id=class_id, status=Enrollment.Status.ACTIVE
        ).count()
        == 3
    )
