from uuid import UUID

from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from hamamooz.apps.core.services import record_audit
from hamamooz.apps.core.viewsets import AuditedModelViewSet
from hamamooz.apps.organizations.models import School

from .access import (
    administered_organization_ids,
    can_manage_role_assignment,
    is_system_admin,
    selected_school_ids,
    user_has_role,
)
from .models import Role, RoleAssignment, User
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RoleAssignmentSerializer,
    UserSerializer,
)

ADMIN_ROLES = [Role.SYSTEM_ADMIN, Role.ORGANIZATION_ADMIN, Role.SCHOOL_MANAGER]


def membership_scope(request):
    school_ids = selected_school_ids(request)
    administered_org_ids = set(administered_organization_ids(request.user))
    selected_organization = request.headers.get("X-Organization-ID")
    if selected_organization:
        selected_organization = UUID(selected_organization)
        administered_org_ids.intersection_update({selected_organization})
        school_ids = list(
            School.objects.filter(
                id__in=school_ids,
                organization_id=selected_organization,
            ).values_list("id", flat=True)
        )
    school_org_ids = set(
        School.objects.filter(id__in=school_ids).values_list("organization_id", flat=True)
    )
    return school_ids, administered_org_ids, school_org_ids


def membership_scope_q(request, prefix="role_assignments__"):
    school_ids, administered_org_ids, school_org_ids = membership_scope(request)
    if request.headers.get("X-School-ID"):
        return Q(**{f"{prefix}school_id__in": school_ids}) | Q(
            **{
                f"{prefix}school__isnull": True,
                f"{prefix}organization_id__in": school_org_ids,
            }
        )
    return Q(**{f"{prefix}organization_id__in": administered_org_ids}) | Q(
        **{f"{prefix}school_id__in": school_ids}
    )


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutSerializer, responses={204: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            return Response({"detail": "توکن تازه‌سازی معتبر نیست."}, status=400)
        record_audit(action="auth.logout", actor=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)


class UserViewSet(AuditedModelViewSet):
    queryset = User.objects.none()
    serializer_class = UserSerializer
    # Users are deactivated, never deleted, so historical audit relations remain intact.
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    search_fields = ["username", "email", "first_name", "last_name", "phone"]
    filterset_fields = ["is_active"]
    required_roles_by_action = {
        action: ADMIN_ROLES for action in ["create", "update", "partial_update", "deactivate"]
    }

    def get_queryset(self):
        if not user_has_role(self.request.user, ADMIN_ROLES):
            return User.objects.filter(id=self.request.user.id).order_by("id")
        return (
            User.objects.filter(
                Q(id=self.request.user.id)
                | (membership_scope_q(self.request) & Q(role_assignments__is_active=True))
            )
            .distinct()
            .order_by("id")
        )

    def _ensure_can_manage_user(self, target):
        if target == self.request.user or is_system_admin(self.request.user):
            return
        assignments = list(
            target.role_assignments.filter(is_active=True).only(
                "role", "organization_id", "school_id"
            )
        )
        if not assignments:
            self.permission_denied(
                self.request, "فقط مدیر کل می‌تواند حساب بدون حوزه فعال را مدیریت کند."
            )
        selected_school = self.request.headers.get("X-School-ID")
        selected_organization = self.request.headers.get("X-Organization-ID")
        for assignment in assignments:
            if selected_school and str(assignment.school_id) != selected_school:
                self.permission_denied(
                    self.request,
                    "حوزه درخواست با تمام نقش‌های فعال این حساب منطبق نیست.",
                )
            if selected_organization and str(assignment.organization_id) != selected_organization:
                self.permission_denied(
                    self.request,
                    "حوزه درخواست با مجموعه نقش فعال این حساب منطبق نیست.",
                )
            if not can_manage_role_assignment(self.request.user, assignment):
                self.permission_denied(
                    self.request,
                    "این حساب در حوزه‌ای خارج از اختیار شما نقش فعال دارد.",
                )

    def perform_update(self, serializer):
        self._ensure_can_manage_user(serializer.instance)
        super().perform_update(serializer)

    @action(detail=True, methods=["post"])
    def change_password(self, request, pk=None):
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if user != request.user:
            self._ensure_can_manage_user(user)
        elif not user.check_password(serializer.validated_data.get("current_password", "")):
            return Response({"current_password": "رمز عبور فعلی نادرست است."}, status=400)
        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        record_audit(
            action="user.password_changed", actor=request.user, request=request, entity=user
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        self._ensure_can_manage_user(user)
        if user == request.user:
            return Response({"detail": "غیرفعال‌کردن حساب خودتان مجاز نیست."}, status=400)
        user.is_active = False
        user.save(update_fields=["is_active"])
        record_audit(action="user.deactivated", actor=request.user, request=request, entity=user)
        return Response(UserSerializer(user).data)


class RoleAssignmentViewSet(AuditedModelViewSet):
    queryset = RoleAssignment.objects.none()
    serializer_class = RoleAssignmentSerializer
    filterset_fields = ["user", "organization", "school", "role", "is_active"]
    required_roles_by_action = {
        action: ADMIN_ROLES for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        if not user_has_role(self.request.user, ADMIN_ROLES):
            return RoleAssignment.objects.filter(user=self.request.user).select_related(
                "user", "organization", "school"
            )
        return RoleAssignment.objects.filter(
            membership_scope_q(self.request, prefix="") | Q(user=self.request.user)
        ).select_related("user", "organization", "school")

    def perform_destroy(self, instance):
        if not can_manage_role_assignment(self.request.user, instance):
            self.permission_denied(
                self.request,
                "اجازه حذف این تخصیص نقش را ندارید.",
            )
        super().perform_destroy(instance)
