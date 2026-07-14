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

from .access import accessible_organization_ids, accessible_school_ids, user_has_role
from .models import Role, RoleAssignment, User
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RoleAssignmentSerializer,
    UserSerializer,
)

ADMIN_ROLES = [Role.SYSTEM_ADMIN, Role.ORGANIZATION_ADMIN, Role.SCHOOL_MANAGER]


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
        action: ADMIN_ROLES
        for action in ["create", "update", "partial_update", "deactivate"]
    }

    def get_queryset(self):
        if not user_has_role(self.request.user, ADMIN_ROLES):
            return User.objects.filter(id=self.request.user.id)
        organization_ids = accessible_organization_ids(self.request.user)
        school_ids = accessible_school_ids(self.request.user)
        return User.objects.filter(
            Q(id=self.request.user.id)
            | Q(
                role_assignments__organization_id__in=organization_ids,
                role_assignments__is_active=True,
            )
            | Q(role_assignments__school_id__in=school_ids, role_assignments__is_active=True)
        ).distinct()

    @action(detail=True, methods=["post"])
    def change_password(self, request, pk=None):
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if user != request.user:
            if not user_has_role(request.user, ADMIN_ROLES):
                self.permission_denied(request, "اجازه تغییر رمز این کاربر را ندارید.")
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
            Q(organization_id__in=accessible_organization_ids(self.request.user))
            | Q(school_id__in=accessible_school_ids(self.request.user))
            | Q(user=self.request.user)
        ).select_related("user", "organization", "school")
