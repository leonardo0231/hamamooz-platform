from __future__ import annotations

from django.db.models import QuerySet

from apps.organizations.models import School


def accessible_schools(user) -> QuerySet[School]:
    if user.is_superuser:
        return School.objects.all()

    return School.objects.filter(
        memberships__user=user,
        memberships__is_active=True,
    ).distinct()