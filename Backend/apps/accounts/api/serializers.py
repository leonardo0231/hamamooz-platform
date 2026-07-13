from __future__ import annotations

from django.contrib.auth import password_validation
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
)

from apps.accounts.exceptions import (
    LoginTemporarilyLocked,
)
from apps.accounts.models import User
from apps.accounts.security import (
    canonicalize_email,
    is_login_locked,
    record_login_attempt,
)


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User

        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
        )

        read_only_fields = fields


class TokenPairResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)

    refresh = serializers.CharField(read_only=True)


class EmailTokenObtainPairSerializer(
    TokenObtainPairSerializer,
):
    username_field = User.USERNAME_FIELD

    def validate(self, attrs: dict) -> dict:
        raw_email = str(
            attrs.get(self.username_field, "")
        )

        email = canonicalize_email(raw_email)

        attrs[self.username_field] = email

        request = self.context.get("request")

        if is_login_locked(email):
            raise LoginTemporarilyLocked()

        try:
            result = super().validate(attrs)
        except AuthenticationFailed:
            record_login_attempt(
                email=email,
                request=request,
                succeeded=False,
            )

            raise

        record_login_attempt(
            email=email,
            request=request,
            succeeded=True,
            user=self.user,
        )

        return result


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True
    )

    new_password = serializers.CharField(
        write_only=True
    )

    def validate_old_password(
        self,
        value: str,
    ) -> str:
        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError(
                "Current password is incorrect."
            )

        return value

    def validate_new_password(
        self,
        value: str,
    ) -> str:
        password_validation.validate_password(
            value,
            self.context["request"].user,
        )

        return value