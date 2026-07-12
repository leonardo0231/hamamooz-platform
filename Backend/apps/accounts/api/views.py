from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.api.serializers import (
    ChangePasswordSerializer,
    EmailTokenObtainPairSerializer,
    LogoutSerializer,
    UserSerializer,
)


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses=UserSerializer)
    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(request=LogoutSerializer, responses={204: None})
    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError as exc:
            raise TokenError("Refresh token is invalid or expired.") from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(request=ChangePasswordSerializer, responses={204: None})
    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)
