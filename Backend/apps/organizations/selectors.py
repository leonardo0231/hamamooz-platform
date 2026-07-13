from __future__ import annotations

from django.db.models import Q, QuerySet

from apps.organizations.models import Organization, School
from apps.permissions.models import SystemRole


def accessible_organizations(user) -> QuerySet[Organization]:
    if not user.is_authenticated:
        return Organization.objects.none()

    if user.is_superuser:
        return Organization.objects.all()

    return Organization.objects.filter(
        schools__memberships__user=user,
        schools__memberships__is_active=True,
    ).distinct()


def accessible_schools(user) -> QuerySet[School]:
    if not user.is_authenticated:
        return School.objects.none()

    if user.is_superuser:
        return School.objects.all()

    managed_organization_ids = user.school_memberships.filter(
        is_active=True,
        roles__role=SystemRole.ORGANIZATION_MANAGER,
    ).values_list(
        "school__organization_id",
        flat=True,
    )

    return School.objects.filter(
        Q(
            memberships__user=user,
            memberships__is_active=True,
        )
        | Q(
            organization_id__in=managed_organization_ids,
        )
    ).distinct()
