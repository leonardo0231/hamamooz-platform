import pytest

from apps.accounts.models import User
from apps.organizations.models import (
    Organization,
    RoleAssignment,
    School,
    SchoolMembership,
)
from apps.permissions.models import SystemRole
from apps.permissions.policies import can_manage_school, has_role


@pytest.fixture
def organization() -> Organization:
    return Organization.objects.create(
        name="HamAmooz Educational Organization",
        code="HAMAMOOZ",
    )


@pytest.fixture
def school_a(organization: Organization) -> School:
    return School.objects.create(
        organization=organization,
        name="School A",
        code="SCHOOL-A",
    )


@pytest.fixture
def school_b(organization: Organization) -> School:
    return School.objects.create(
        organization=organization,
        name="School B",
        code="SCHOOL-B",
    )


@pytest.fixture
def user() -> User:
    return User.objects.create_user(
        email="manager@example.com",
        password="StrongPass-12345",
    )


@pytest.mark.django_db
def test_has_role_returns_true_for_active_membership(
    user: User,
    school_a: School,
) -> None:
    membership = SchoolMembership.objects.create(
        user=user,
        school=school_a,
        is_active=True,
    )

    RoleAssignment.objects.create(
        membership=membership,
        role=SystemRole.SCHOOL_MANAGER,
    )

    assert has_role(user, SystemRole.SCHOOL_MANAGER) is True


@pytest.mark.django_db
def test_has_role_returns_false_for_inactive_membership(
    user: User,
    school_a: School,
) -> None:
    membership = SchoolMembership.objects.create(
        user=user,
        school=school_a,
        is_active=False,
    )

    RoleAssignment.objects.create(
        membership=membership,
        role=SystemRole.SCHOOL_MANAGER,
    )

    assert has_role(user, SystemRole.SCHOOL_MANAGER) is False


@pytest.mark.django_db
def test_has_role_returns_false_for_unassigned_role(
    user: User,
    school_a: School,
) -> None:
    membership = SchoolMembership.objects.create(
        user=user,
        school=school_a,
        is_active=True,
    )

    RoleAssignment.objects.create(
        membership=membership,
        role=SystemRole.TEACHER,
    )

    assert has_role(user, SystemRole.SCHOOL_MANAGER) is False


@pytest.mark.django_db
def test_school_manager_can_manage_own_school(
    user: User,
    school_a: School,
) -> None:
    membership = SchoolMembership.objects.create(
        user=user,
        school=school_a,
        is_active=True,
    )

    RoleAssignment.objects.create(
        membership=membership,
        role=SystemRole.SCHOOL_MANAGER,
    )

    assert can_manage_school(user, school_a) is True


@pytest.mark.django_db
def test_school_manager_cannot_manage_another_school(
    user: User,
    school_a: School,
    school_b: School,
) -> None:
    membership = SchoolMembership.objects.create(
        user=user,
        school=school_a,
        is_active=True,
    )

    RoleAssignment.objects.create(
        membership=membership,
        role=SystemRole.SCHOOL_MANAGER,
    )

    assert can_manage_school(user, school_b) is False


@pytest.mark.django_db
def test_teacher_cannot_manage_school(
    user: User,
    school_a: School,
) -> None:
    membership = SchoolMembership.objects.create(
        user=user,
        school=school_a,
        is_active=True,
    )

    RoleAssignment.objects.create(
        membership=membership,
        role=SystemRole.TEACHER,
    )

    assert can_manage_school(user, school_a) is False


@pytest.mark.django_db
def test_superuser_can_manage_every_school(
    organization: Organization,
    school_a: School,
    school_b: School,
) -> None:
    superuser = User.objects.create_superuser(
        email="system-admin@example.com",
        password="StrongPass-12345",
    )

    assert can_manage_school(superuser, school_a) is True
    assert can_manage_school(superuser, school_b) is True