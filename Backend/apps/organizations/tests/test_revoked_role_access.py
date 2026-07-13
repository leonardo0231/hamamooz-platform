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


@pytest.mark.django_db
def test_revoked_organization_manager_cannot_update() -> None:
    organization = Organization.objects.create(
        name="Organization",
        code="ORG",
    )

    school = School.objects.create(
        organization=organization,
        name="School",
        code="SCH",
    )

    manager = User.objects.create_user(
        email="manager@example.com",
        password="StrongPass-12345",
    )

    membership = SchoolMembership.objects.create(
        user=manager,
        school=school,
    )

    assignment = RoleAssignment.objects.create(
        membership=membership,
        role=SystemRole.ORGANIZATION_MANAGER,
        is_active=True,
    )

    client = APIClient()
    client.force_authenticate(user=manager)

    allowed_response = client.patch(
        reverse(
            "organization-detail",
            kwargs={
                "pk": organization.pk,
            },
        ),
        {
            "name": "Allowed Name",
        },
        format="json",
    )

    assert (
        allowed_response.status_code
        == status.HTTP_200_OK
    )

    assignment.is_active = False
    assignment.save(
        update_fields=(
            "is_active",
            "updated_at",
        )
    )

    denied_response = client.patch(
        reverse(
            "organization-detail",
            kwargs={
                "pk": organization.pk,
            },
        ),
        {
            "name": "Forbidden Name",
        },
        format="json",
    )

    assert (
        denied_response.status_code
        == status.HTTP_404_NOT_FOUND
    )

    organization.refresh_from_db()

    assert organization.name == "Allowed Name"