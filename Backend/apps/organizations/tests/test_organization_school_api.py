import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.organizations.models import (
    Organization,
    RoleAssignment,
    School,
    SchoolMembership,
)
from apps.permissions.models import SystemRole


def grant_role(
    user: User,
    school: School,
    role: str,
) -> SchoolMembership:
    membership = SchoolMembership.objects.create(
        user=user,
        school=school,
        is_active=True,
    )

    RoleAssignment.objects.create(
        membership=membership,
        role=role,
    )

    return membership


def authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def organization_a() -> Organization:
    return Organization.objects.create(
        name="Organization A",
        code="ORG-A",
    )


@pytest.fixture
def organization_b() -> Organization:
    return Organization.objects.create(
        name="Organization B",
        code="ORG-B",
    )


@pytest.fixture
def school_a(
    organization_a: Organization,
) -> School:
    return School.objects.create(
        organization=organization_a,
        name="School A",
        code="SCHOOL-A",
    )


@pytest.fixture
def school_b(
    organization_b: Organization,
) -> School:
    return School.objects.create(
        organization=organization_b,
        name="School B",
        code="SCHOOL-B",
    )


@pytest.mark.django_db
def test_teacher_only_sees_own_organization_and_school(
    organization_a: Organization,
    organization_b: Organization,
    school_a: School,
    school_b: School,
) -> None:
    teacher = User.objects.create_user(
        email="teacher@example.com",
        password="StrongPass-12345",
    )

    grant_role(
        teacher,
        school_a,
        SystemRole.TEACHER,
    )

    client = authenticated_client(teacher)

    organizations_response = client.get(
        reverse("organization-list"),
    )

    assert organizations_response.status_code == status.HTTP_200_OK

    organization_ids = {
        item["id"]
        for item in organizations_response.json()["results"]
    }

    assert organization_ids == {organization_a.id}
    assert organization_b.id not in organization_ids

    schools_response = client.get(
        reverse("school-list"),
    )

    assert schools_response.status_code == status.HTTP_200_OK

    school_ids = {
        item["id"]
        for item in schools_response.json()["results"]
    }

    assert school_ids == {school_a.id}
    assert school_b.id not in school_ids


@pytest.mark.django_db
def test_teacher_cannot_retrieve_another_school(
    school_a: School,
    school_b: School,
) -> None:
    teacher = User.objects.create_user(
        email="teacher@example.com",
        password="StrongPass-12345",
    )

    grant_role(
        teacher,
        school_a,
        SystemRole.TEACHER,
    )

    response = authenticated_client(teacher).get(
        reverse(
            "school-detail",
            kwargs={"pk": school_b.pk},
        )
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "not_found"


@pytest.mark.django_db
def test_organization_manager_sees_all_schools_of_own_organization(
    organization_a: Organization,
    organization_b: Organization,
    school_a: School,
    school_b: School,
) -> None:
    second_school_in_a = School.objects.create(
        organization=organization_a,
        name="Second School A",
        code="SCHOOL-A-2",
    )

    manager = User.objects.create_user(
        email="organization-manager@example.com",
        password="StrongPass-12345",
    )

    grant_role(
        manager,
        school_a,
        SystemRole.ORGANIZATION_MANAGER,
    )

    response = authenticated_client(manager).get(
        reverse("school-list"),
    )

    assert response.status_code == status.HTTP_200_OK

    school_ids = {
        item["id"]
        for item in response.json()["results"]
    }

    assert school_ids == {
        school_a.id,
        second_school_in_a.id,
    }

    assert school_b.id not in school_ids
    assert organization_b.id != organization_a.id


@pytest.mark.django_db
def test_non_superuser_cannot_create_organization(
    school_a: School,
) -> None:
    manager = User.objects.create_user(
        email="organization-manager@example.com",
        password="StrongPass-12345",
    )

    grant_role(
        manager,
        school_a,
        SystemRole.ORGANIZATION_MANAGER,
    )

    response = authenticated_client(manager).post(
        reverse("organization-list"),
        {
            "name": "Forbidden Organization",
            "code": "FORBIDDEN",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "permission_denied"


@pytest.mark.django_db
def test_organization_manager_can_update_own_organization_name(
    organization_a: Organization,
    school_a: School,
) -> None:
    manager = User.objects.create_user(
        email="organization-manager@example.com",
        password="StrongPass-12345",
    )

    grant_role(
        manager,
        school_a,
        SystemRole.ORGANIZATION_MANAGER,
    )

    response = authenticated_client(manager).patch(
        reverse(
            "organization-detail",
            kwargs={"pk": organization_a.pk},
        ),
        {
            "name": "Updated Organization A",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    organization_a.refresh_from_db()

    assert organization_a.name == "Updated Organization A"


@pytest.mark.django_db
def test_organization_manager_cannot_change_organization_code(
    organization_a: Organization,
    school_a: School,
) -> None:
    manager = User.objects.create_user(
        email="organization-manager@example.com",
        password="StrongPass-12345",
    )

    grant_role(
        manager,
        school_a,
        SystemRole.ORGANIZATION_MANAGER,
    )

    response = authenticated_client(manager).patch(
        reverse(
            "organization-detail",
            kwargs={"pk": organization_a.pk},
        ),
        {
            "code": "CHANGED-CODE",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "organization_access_denied"

    organization_a.refresh_from_db()

    assert organization_a.code == "ORG-A"


@pytest.mark.django_db
def test_organization_manager_can_create_school_in_own_organization(
    organization_a: Organization,
    school_a: School,
) -> None:
    manager = User.objects.create_user(
        email="organization-manager@example.com",
        password="StrongPass-12345",
    )

    grant_role(
        manager,
        school_a,
        SystemRole.ORGANIZATION_MANAGER,
    )

    response = authenticated_client(manager).post(
        reverse("school-list"),
        {
            "organization_id": organization_a.id,
            "name": "New School",
            "code": "NEW-SCHOOL",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    assert School.objects.filter(
        organization=organization_a,
        code="NEW-SCHOOL",
    ).exists()


@pytest.mark.django_db
def test_school_manager_cannot_create_school(
    organization_a: Organization,
    school_a: School,
) -> None:
    manager = User.objects.create_user(
        email="school-manager@example.com",
        password="StrongPass-12345",
    )

    grant_role(
        manager,
        school_a,
        SystemRole.SCHOOL_MANAGER,
    )

    response = authenticated_client(manager).post(
        reverse("school-list"),
        {
            "organization_id": organization_a.id,
            "name": "Forbidden School",
            "code": "FORBIDDEN-SCHOOL",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "school_access_denied"


@pytest.mark.django_db
def test_school_manager_can_edit_name_but_cannot_deactivate_school(
    school_a: School,
) -> None:
    manager = User.objects.create_user(
        email="school-manager@example.com",
        password="StrongPass-12345",
    )

    grant_role(
        manager,
        school_a,
        SystemRole.SCHOOL_MANAGER,
    )

    client = authenticated_client(manager)

    name_response = client.patch(
        reverse(
            "school-detail",
            kwargs={"pk": school_a.pk},
        ),
        {
            "name": "Updated School Name",
        },
        format="json",
    )

    assert name_response.status_code == status.HTTP_200_OK

    school_a.refresh_from_db()

    assert school_a.name == "Updated School Name"

    deactivate_response = client.patch(
        reverse(
            "school-detail",
            kwargs={"pk": school_a.pk},
        ),
        {
            "is_active": False,
        },
        format="json",
    )

    assert deactivate_response.status_code == status.HTTP_403_FORBIDDEN
    assert deactivate_response.json()["code"] == "school_access_denied"

    school_a.refresh_from_db()

    assert school_a.is_active is True
