from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.organizations.models import Organization, School
from apps.permissions.policies import (
    can_manage_organization,
    can_manage_school,
)


class OrganizationAccessPermission(BasePermission):
    def has_permission(
        self,
        request: Request,
        view: APIView,
    ) -> bool:
        if not request.user.is_authenticated:
            return False

        action = getattr(view, "action", None)

        if action == "create":
            return request.user.is_superuser

        if action == "destroy":
            return False

        return True

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: Organization,
    ) -> bool:
        if request.method in SAFE_METHODS:
            return True

        action = getattr(view, "action", None)

        if action in {"update", "partial_update"}:
            return can_manage_organization(
                request.user,
                obj,
            )

        return False


class SchoolAccessPermission(BasePermission):
    def has_permission(
        self,
        request: Request,
        view: APIView,
    ) -> bool:
        if not request.user.is_authenticated:
            return False

        action = getattr(view, "action", None)

        if action == "destroy":
            return False

        return True

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: School,
    ) -> bool:
        if request.method in SAFE_METHODS:
            return True

        action = getattr(view, "action", None)

        if action in {"update", "partial_update"}:
            return can_manage_school(
                request.user,
                obj,
            )

        return False
