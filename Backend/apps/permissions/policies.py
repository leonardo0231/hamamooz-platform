from __future__ import annotations

from typing import TYPE_CHECKING

from apps.permissions.models import SystemRole

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.organizations.models import Organization, School


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
        roles__role=role,
    )

    if school is not None:
        memberships = memberships.filter(school=school)

    if organization is not None:
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
    if user.is_superuser:
        return True

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
