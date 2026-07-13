import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts.models import User
from apps.organizations.models import (
    Organization,
    School,
)


@pytest.mark.django_db
def test_staff_with_model_permissions_cannot_access_school_admin(
    client,
) -> None:
    staff = User.objects.create_user(
        email="staff@example.com",
        password="StrongPass-12345",
        is_staff=True,
    )

    permissions = Permission.objects.filter(
        content_type__app_label="organizations",
    )

    staff.user_permissions.set(permissions)

    client.force_login(staff)

    response = client.get(
        reverse(
            "admin:organizations_school_changelist"
        )
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_staff_cannot_access_user_admin(
    client,
) -> None:
    staff = User.objects.create_user(
        email="staff@example.com",
        password="StrongPass-12345",
        is_staff=True,
    )

    permissions = Permission.objects.filter(
        content_type__app_label="accounts",
    )

    staff.user_permissions.set(permissions)

    client.force_login(staff)

    response = client.get(
        reverse("admin:accounts_user_changelist")
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_superuser_cannot_hard_delete_organization_from_admin(
    client,
) -> None:
    superuser = User.objects.create_superuser(
        email="root@example.com",
        password="StrongPass-12345",
    )

    organization = Organization.objects.create(
        name="Organization",
        code="ORG",
    )

    School.objects.create(
        organization=organization,
        name="School",
        code="SCH",
    )

    client.force_login(superuser)

    response = client.get(
        reverse(
            "admin:organizations_organization_delete",
            args=(organization.pk,),
        )
    )

    assert response.status_code == 403

    assert Organization.objects.filter(
        pk=organization.pk
    ).exists()