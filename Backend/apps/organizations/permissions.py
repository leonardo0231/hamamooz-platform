from __future__ import annotations

from typing import TYPE_CHECKING

from apps.permissions.models import SystemRole

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.organizations.models import (
        Organization,
        School,
        SchoolMembership,
    )


def has_role(
    user: User,
    role: str,
    *,
    school: School | None = None,
    organization: Organization | None = None,
) -> bool:
    if not user.is_authenticated or not user.is_active:
        return False

    memberships = user.school_memberships.filter(
        is_active=True,
        school__is_active=True,
        school__organization__is_active=True,
        roles__role=role,
        roles__is_active=True,
    )

    if school is not None:
        if not school.is_active or not school.organization.is_active:
            return False

        memberships = memberships.filter(school=school)

    if organization is not None:
        if not organization.is_active:
            return False

        memberships = memberships.filter(
            school__organization=organization,
        )

    return memberships.exists()


def can_manage_organization(
    user: User,
    organization: Organization,
) -> bool:
    if user.is_superuser:
        return True

    if not organization.is_active:
        return False

    return has_role(
        user,
        SystemRole.ORGANIZATION_MANAGER,
        organization=organization,
    )


def can_create_school_in_organization(
    user: User,
    organization: Organization,
) -> bool:
    return can_manage_organization(user, organization)


def can_manage_school(
    user: User,
    school: School,
) -> bool:
    """
    Manage the School record itself.

    School managers are intentionally read-only for the School entity.
    """

    if user.is_superuser:
        return True

    if not school.is_active or not school.organization.is_active:
        return False

    return has_role(
        user,
        SystemRole.ORGANIZATION_MANAGER,
        organization=school.organization,
    )


def can_manage_school_memberships(
    user: User,
    school: School,
) -> bool:
    if user.is_superuser:
        return True

    if not school.is_active or not school.organization.is_active:
        return False

    if has_role(
        user,
        SystemRole.ORGANIZATION_MANAGER,
        organization=school.organization,
    ):
        return True

    return has_role(
        user,
        SystemRole.SCHOOL_MANAGER,
        school=school,
    )


def can_manage_membership(
    user: User,
    membership: SchoolMembership,
) -> bool:
    return can_manage_school_memberships(
        user,
        membership.school,
    )


def can_grant_role(
    user: User,
    membership: SchoolMembership,
    role: str,
) -> bool:
    if role not in SystemRole.values:
        return False

    if user.is_superuser:
        return True

    if not membership.is_active:
        return False

    school = membership.school

    if role == SystemRole.ORGANIZATION_MANAGER:
        return False

    if role == SystemRole.SCHOOL_MANAGER:
        return has_role(
            user,
            SystemRole.ORGANIZATION_MANAGER,
            organization=school.organization,
        )

    return can_manage_school_memberships(
        user,
        school,
    )