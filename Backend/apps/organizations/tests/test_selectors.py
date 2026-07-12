import pytest

from apps.accounts.models import User
from apps.organizations.models import (
    Organization,
    School,
    SchoolMembership,
)
from apps.organizations.selectors import accessible_schools


@pytest.fixture
def organization() -> Organization:
    return Organization.objects.create(
        name="HamAmooz Educational Organization",
        code="HAMAMOOZ",
    )


@pytest.fixture
def user() -> User:
    return User.objects.create_user(
        email="user@example.com",
        password="StrongPass-12345",
    )


@pytest.mark.django_db
def test_accessible_schools_returns_only_active_memberships(
    organization: Organization,
    user: User,
) -> None:
    school_a = School.objects.create(
        organization=organization,
        name="School A",
        code="SCHOOL-A",
    )

    school_b = School.objects.create(
        organization=organization,
        name="School B",
        code="SCHOOL-B",
    )

    school_c = School.objects.create(
        organization=organization,
        name="School C",
        code="SCHOOL-C",
    )

    SchoolMembership.objects.create(
        user=user,
        school=school_a,
        is_active=True,
    )

    SchoolMembership.objects.create(
        user=user,
        school=school_b,
        is_active=False,
    )

    accessible_ids = set(
        accessible_schools(user).values_list("id", flat=True)
    )

    assert accessible_ids == {school_a.id}
    assert school_b.id not in accessible_ids
    assert school_c.id not in accessible_ids


@pytest.mark.django_db
def test_superuser_can_access_all_schools(
    organization: Organization,
) -> None:
    school_a = School.objects.create(
        organization=organization,
        name="School A",
        code="SCHOOL-A",
    )

    school_b = School.objects.create(
        organization=organization,
        name="School B",
        code="SCHOOL-B",
    )

    superuser = User.objects.create_superuser(
        email="system-admin@example.com",
        password="StrongPass-12345",
    )

    accessible_ids = set(
        accessible_schools(superuser).values_list("id", flat=True)
    )

    assert accessible_ids == {
        school_a.id,
        school_b.id,
    }