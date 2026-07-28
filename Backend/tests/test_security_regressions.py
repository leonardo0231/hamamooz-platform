from datetime import date

import pytest
from django.db import IntegrityError, transaction

from hamamooz.apps.academics.models import CalculationPolicy
from hamamooz.apps.accounts.models import Role, RoleAssignment, User
from hamamooz.apps.core.models import AuditEvent
from hamamooz.apps.students.models import Enrollment, Student


def create_student(base_data, national_id="0012345690"):
    return Student.objects.create(
        organization=base_data["organization"],
        national_id=national_id,
        first_name="دانش‌آموز",
        last_name="جدید",
        birth_date=date(2012, 4, 1),
        gender=Student.Gender.FEMALE,
    )


def enrollment_payload(base_data, student, *, school_key="school1", class_key="class1"):
    return {
        "student": str(student.id),
        "school": str(base_data[school_key].id),
        "academic_year": str(base_data["year"].id),
        "grade_level": str(base_data["grade"].id),
        "class_section": str(base_data[class_key].id),
        "student_number": f"new-{student.national_id}",
        "status": Enrollment.Status.ACTIVE,
        "enrolled_on": "2026-09-23",
    }


@pytest.mark.django_db
def test_write_requires_explicit_scope_for_non_system_admin(api_client, base_data):
    student = create_student(base_data)
    api_client.force_authenticate(base_data["manager"])

    response = api_client.post(
        "/api/v1/enrollments/",
        enrollment_payload(base_data, student),
        format="json",
    )

    assert response.status_code == 403
    assert not Enrollment.objects.filter(student=student).exists()


@pytest.mark.django_db
def test_role_from_one_school_cannot_write_to_another_school(api_client, base_data):
    actor = base_data["teacher2"]
    RoleAssignment.objects.create(
        user=actor,
        organization=base_data["organization"],
        school=base_data["school1"],
        role=Role.OPERATOR,
    )
    RoleAssignment.objects.create(
        user=actor,
        organization=base_data["organization"],
        school=base_data["school2"],
        role=Role.OPERATOR,
    )
    student = create_student(base_data)
    api_client.force_authenticate(actor)

    response = api_client.post(
        "/api/v1/enrollments/",
        enrollment_payload(base_data, student, school_key="school2", class_key="class2"),
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 403
    assert not Enrollment.objects.filter(student=student).exists()


@pytest.mark.django_db
def test_valid_scoped_write_succeeds_and_is_audited(api_client, base_data):
    student = create_student(base_data)
    api_client.force_authenticate(base_data["manager"])

    response = api_client.post(
        "/api/v1/enrollments/",
        enrollment_payload(base_data, student),
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 201
    enrollment = Enrollment.objects.get(student=student)
    assert AuditEvent.objects.filter(
        action="create",
        entity_id=str(enrollment.id),
        school_id=base_data["school1"].id,
    ).exists()


@pytest.mark.django_db
def test_invalid_scope_header_returns_forbidden_instead_of_server_error(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])
    response = api_client.patch(
        f"/api/v1/users/{base_data['teacher1'].id}/",
        {"first_name": "نام"},
        format="json",
        HTTP_X_SCHOOL_ID="not-a-uuid",
    )
    assert response.status_code == 403
    read_response = api_client.get(
        "/api/v1/users/",
        HTTP_X_SCHOOL_ID="not-a-uuid",
    )
    assert read_response.status_code == 403


@pytest.mark.django_db
def test_branch_manager_membership_lists_do_not_leak_other_branch(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])

    users = api_client.get(
        "/api/v1/users/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assignments = api_client.get(
        "/api/v1/role-assignments/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    user_ids = {item["id"] for item in users.data["results"]}
    assignment_ids = {item["id"] for item in assignments.data["results"]}
    assert base_data["teacher1"].id in user_ids
    assert base_data["teacher2"].id not in user_ids
    assert not base_data["teacher2"].role_assignments.filter(id__in=assignment_ids).exists()


@pytest.mark.django_db
def test_branch_manager_cannot_deactivate_user_shared_with_another_branch(api_client, base_data):
    target = base_data["teacher1"]
    RoleAssignment.objects.create(
        user=target,
        organization=base_data["organization"],
        school=base_data["school2"],
        role=Role.TEACHER,
    )
    api_client.force_authenticate(base_data["manager"])

    response = api_client.post(
        f"/api/v1/users/{target.id}/deactivate/",
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 403
    target.refresh_from_db()
    assert target.is_active is True


@pytest.mark.django_db
def test_branch_manager_cannot_manage_organization_admin(api_client, base_data):
    organization_admin = User.objects.create_user(
        username="organization-admin",
        email="organization-admin@example.com",
        password="Strong-pass-123",
    )
    assignment = RoleAssignment.objects.create(
        user=organization_admin,
        organization=base_data["organization"],
        role=Role.ORGANIZATION_ADMIN,
    )
    api_client.force_authenticate(base_data["manager"])

    deactivate = api_client.post(
        f"/api/v1/users/{organization_admin.id}/deactivate/",
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    delete_role = api_client.delete(
        f"/api/v1/role-assignments/{assignment.id}/",
        HTTP_X_ORGANIZATION_ID=str(base_data["organization"].id),
    )
    demote_role = api_client.patch(
        f"/api/v1/role-assignments/{assignment.id}/",
        {
            "role": Role.OPERATOR,
            "school": str(base_data["school1"].id),
        },
        format="json",
        HTTP_X_ORGANIZATION_ID=str(base_data["organization"].id),
    )

    assert deactivate.status_code == 403
    assert delete_role.status_code == 404
    assert demote_role.status_code == 404
    organization_admin.refresh_from_db()
    assignment.refresh_from_db()
    assert organization_admin.is_active is True
    assert assignment.is_deleted is False


@pytest.mark.django_db
def test_password_cannot_be_changed_through_generic_user_update(api_client, base_data):
    user = base_data["manager"]
    api_client.force_authenticate(user)

    response = api_client.patch(
        f"/api/v1/users/{user.id}/",
        {"password": "Bypass-current-password-456"},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password("Strong-pass-123")


@pytest.mark.django_db
def test_audited_update_records_non_sensitive_before_and_after_values(api_client, base_data):
    target = base_data["teacher1"]
    api_client.force_authenticate(base_data["manager"])

    response = api_client.patch(
        f"/api/v1/users/{target.id}/",
        {"first_name": "علی"},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    event = AuditEvent.objects.filter(action="update", entity_id=str(target.id)).latest(
        "created_at"
    )
    assert event.changes == {
        "before": {"first_name": ""},
        "after": {"first_name": "علی"},
    }


@pytest.mark.django_db
def test_nullable_role_scopes_are_uniquely_constrained(base_data):
    user = User.objects.create_user(
        username="system-duplicate",
        email="system-duplicate@example.com",
        password="Strong-pass-123",
    )
    RoleAssignment.objects.create(user=user, role=Role.SYSTEM_ADMIN)

    with pytest.raises(IntegrityError), transaction.atomic():
        RoleAssignment.objects.create(user=user, role=Role.SYSTEM_ADMIN)


@pytest.mark.django_db
def test_nullable_calculation_policy_scope_is_uniquely_constrained(base_data):
    CalculationPolicy.objects.create(
        organization=base_data["organization"],
        version="unique-org-v1",
        title="نسخه اول",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        CalculationPolicy.objects.create(
            organization=base_data["organization"],
            version="unique-org-v1",
            title="نسخه تکراری",
        )


@pytest.mark.django_db
def test_calculation_policy_api_is_append_only(api_client, base_data):
    policy = CalculationPolicy.objects.get(
        organization=base_data["organization"], academic_year=base_data["year"]
    )
    api_client.force_authenticate(base_data["deputy"])

    response = api_client.patch(
        f"/api/v1/calculation-policies/{policy.id}/",
        {"title": "ویرایش غیرمجاز"},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 405
