from rest_framework.permissions import SAFE_METHODS, BasePermission

from hamamooz.apps.core.tenancy import object_organization_id, object_school_id

from .access import accessible_organization_ids, accessible_school_ids, user_has_role


class RolePermission(BasePermission):
    message = "برای انجام این عملیات دسترسی کافی ندارید."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        roles = getattr(view, "required_roles_by_action", {}).get(getattr(view, "action", ""))
        if not roles:
            return True
        selected_school = request.headers.get("X-School-ID")
        organization = request.headers.get("X-Organization-ID")
        return user_has_role(
            request.user,
            roles,
            organization_id=organization,
            school_id=selected_school,
        )

    def has_object_permission(self, request, view, obj):
        organization_id = object_organization_id(obj)
        school_id = object_school_id(obj)
        if school_id and school_id not in set(accessible_school_ids(request.user)):
            return False
        if organization_id and organization_id not in set(
            accessible_organization_ids(request.user)
        ):
            return False
        if request.method in SAFE_METHODS:
            return True
        roles = getattr(view, "required_roles_by_action", {}).get(getattr(view, "action", ""))
        return not roles or user_has_role(
            request.user, roles, organization_id=organization_id, school_id=school_id
        )
