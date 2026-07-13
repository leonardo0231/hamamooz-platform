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
from apps.organizations.selectors import (
    accessible_organizations,
    accessible_schools,
)
from apps.organizations.policies import (
    can_manage_organization,
)

from apps.permissions.models import SystemRole


@pytest.fixture
def manager() -> User:
    return User.objects.create_user(
        email="manager@example.com",
        password="StrongPass-12345",
    )


@pytest.fixture
def organization() -> Organization:
    return Organization.objects.create(
        name="Organization",
        code="ORG",
    )


@pytest.fixture
def school(
    organization: Organization,
) -> School:
    return School.objects.create(
        organization=organization,
        name="School",
        code="SCH",
    )


def assign_manager(
    user: User,
    school: School,
) -> None:
    membership = SchoolMembership.objects.create(
        user=user,
        school=school,
    )

    RoleAssignment.objects.create(
        membership=membership,
        role=SystemRole.ORGANIZATION_MANAGER,
    )


@pytest.mark.django_db
def test_inactive_school_cuts_operational_access(
    manager: User,
    organization: Organization,
    school: School,
) -> None:
    assign_manager(manager, school)

    school.is_active = False
    school.save(update_fields=("is_active",))

    assert not accessible_schools(
        manager
    ).exists()

    assert not accessible_organizations(
        manager
    ).exists()

    assert (
        can_manage_organization(
            manager,
            organization,
        )
        is False
    )


@pytest.mark.django_db
def test_inactive_organization_cuts_operational_access(
    manager: User,
    organization: Organization,
    school: School,
) -> None:
    assign_manager(manager, school)

    organization.is_active = False

    organization.save(
        update_fields=("is_active",)
    )

    assert not accessible_schools(
        manager
    ).exists()

    assert not accessible_organizations(
        manager
    ).exists()

    assert (
        can_manage_organization(
            manager,
            organization,
        )
        is False
    )


@pytest.mark.django_db
def test_inactive_organization_manager_cannot_create_school(
    manager: User,
    organization: Organization,
    school: School,
) -> None:
    assign_manager(manager, school)

    organization.is_active = False

    organization.save(
        update_fields=("is_active",)
    )

    client = APIClient()

    client.force_authenticate(user=manager)

    response = client.post(
        reverse("school-list"),
        {
            "organization_id": organization.pk,
            "name": "Forbidden School",
            "code": "FORBIDDEN",
        },
        format="json",
    )

    assert response.status_code in {
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_403_FORBIDDEN,
    }

    assert not School.objects.filter(
        code="FORBIDDEN"
    ).exists()