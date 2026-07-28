from uuid import UUID

from rest_framework.permissions import SAFE_METHODS, BasePermission

from hamamooz.apps.core.tenancy import object_organization_id, object_school_id
from hamamooz.apps.organizations.models import School

from .access import (
    accessible_organization_ids,
    accessible_school_ids,
    is_system_admin,
    user_has_role,
)


class RolePermission(BasePermission):
    message = "برای انجام این عملیات دسترسی کافی ندارید."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        allowed_methods = getattr(view, "http_method_names", [])
        if request.method.lower() not in allowed_methods:
            return True

        selected_school = request.headers.get("X-School-ID")
        organization = request.headers.get("X-Organization-ID")
        try:
            selected_school = UUID(selected_school) if selected_school else None
            organization = UUID(organization) if organization else None
        except (TypeError, ValueError):
            return False
        if selected_school:
            school_organization = (
                School.objects.filter(id=selected_school)
                .values_list("organization_id", flat=True)
                .first()
            )
            if (
                not school_organization
                or selected_school not in set(accessible_school_ids(request.user))
                or (organization and str(organization) != str(school_organization))
            ):
                return False
        if organization and organization not in set(accessible_organization_ids(request.user)):
            return False
        if request.method in SAFE_METHODS:
            return True
        roles = getattr(view, "required_roles_by_action", {}).get(getattr(view, "action", ""))
        if not roles:
            return False
        if not selected_school and not organization:
            return is_system_admin(request.user)
        return user_has_role(
            request.user,
            roles,
            organization_id=organization,
            school_id=selected_school,
        )

    def has_object_permission(self, request, view, obj):
        organization_id = object_organization_id(obj)
        school_id = object_school_id(obj)
        try:
            selected_school = request.headers.get("X-School-ID")
            selected_school = UUID(selected_school) if selected_school else None
            selected_organization = request.headers.get("X-Organization-ID")
            selected_organization = UUID(selected_organization) if selected_organization else None
        except (TypeError, ValueError):
            return False
        if selected_school:
            if school_id and str(school_id) != str(selected_school):
                return False
            selected_school_organization = (
                School.objects.filter(id=selected_school)
                .values_list("organization_id", flat=True)
                .first()
            )
            if not selected_school_organization:
                return False
            if organization_id and str(organization_id) != str(selected_school_organization):
                return False
        if (
            selected_organization
            and organization_id
            and str(organization_id) != str(selected_organization)
        ):
            return False
        if school_id and school_id not in set(accessible_school_ids(request.user)):
            return False
        if organization_id and organization_id not in set(
            accessible_organization_ids(request.user)
        ):
            return False
        if request.method in SAFE_METHODS:
            return True
        roles = getattr(view, "required_roles_by_action", {}).get(getattr(view, "action", ""))
        if not roles:
            return False
        return user_has_role(
            request.user, roles, organization_id=organization_id, school_id=school_id
        )
