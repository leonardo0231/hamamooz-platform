from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest


class SuperuserOnlyAdminMixin:
    
    @staticmethod
    def _is_allowed(request: HttpRequest) -> bool:
        user = request.user
        return bool(
            user.is_authenticated
            and user.is_active
            and user.is_superuser
        )
        
    def has_module_permission(self, request: HttpRequest) -> bool:
        return self._is_allowed(request)
    
    def has_view_permission(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> bool:
        return self._is_allowed(request)
    
    def has_add_permission(self, request: HttpRequest) -> bool:
        return self._is_allowed(request)

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> bool:
        return self._is_allowed(request)

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> bool:
        return self._is_allowed(request)
    
class NoHardDeleteAdminMixin:
    """Disable object and bulk deletion from Django Admin."""

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> bool:
        return False

    def get_actions(self, request: HttpRequest):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


class SuperuserReadOnlyAdminMixin(
    SuperuserOnlyAdminMixin,
    NoHardDeleteAdminMixin,
):
    """Allow superusers to inspect records without mutating them."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> bool:
        return False