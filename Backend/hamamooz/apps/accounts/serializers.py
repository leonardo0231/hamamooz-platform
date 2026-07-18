from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from hamamooz.apps.core.services import record_audit

from .access import (
    accessible_organization_ids,
    accessible_school_ids,
    can_manage_role_assignment,
    is_system_admin,
    user_has_role,
)
from .models import Role, RoleAssignment, User


class RoleAssignmentSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "user",
            "organization",
            "school",
            "role",
            "role_display",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "role_display", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance or RoleAssignment()
        for key, value in attrs.items():
            setattr(instance, key, value)
        instance.full_clean(exclude=["id"])
        request = self.context.get("request")
        if request and not request.user.is_superuser:
            if self.instance:
                original = RoleAssignment.objects.get(pk=self.instance.pk)
                if not can_manage_role_assignment(request.user, original):
                    raise serializers.ValidationError("اجازه تغییر تخصیص نقش فعلی را ندارید.")
            organization = attrs.get("organization", getattr(instance, "organization", None))
            school = attrs.get("school", getattr(instance, "school", None))
            if organization and organization.id not in set(
                accessible_organization_ids(request.user)
            ):
                raise serializers.ValidationError("به مجموعه انتخاب‌شده دسترسی ندارید.")
            if school and school.id not in set(accessible_school_ids(request.user)):
                raise serializers.ValidationError("به شعبه انتخاب‌شده دسترسی ندارید.")
            target_role = attrs.get("role", instance.role)
            if not is_system_admin(request.user):
                if target_role == Role.SYSTEM_ADMIN:
                    raise serializers.ValidationError("فقط مدیر کل می‌تواند مدیر کل دیگری بسازد.")
                if target_role == Role.ORGANIZATION_ADMIN and not user_has_role(
                    request.user,
                    [Role.ORGANIZATION_ADMIN],
                    organization_id=organization.id if organization else None,
                ):
                    raise serializers.ValidationError("اجازه تخصیص نقش مدیر مجموعه را ندارید.")
                if target_role == Role.SCHOOL_MANAGER and not user_has_role(
                    request.user,
                    [Role.ORGANIZATION_ADMIN],
                    organization_id=organization.id if organization else None,
                ):
                    raise serializers.ValidationError("اجازه تخصیص نقش مدیر شعبه را ندارید.")
        return attrs


class UserSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "full_name", "is_active"]


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=False, validators=[validate_password]
    )
    role_assignments = RoleAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "national_id",
            "is_active",
            "must_change_password",
            "role_assignments",
            "last_login",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "must_change_password",
            "last_login",
            "date_joined",
            "role_assignments",
        ]

    def validate(self, attrs):
        if self.instance and "password" in attrs:
            raise serializers.ValidationError(
                {"password": "برای تغییر رمز از عملیات change_password استفاده کنید."}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "رمز عبور الزامی است."})
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class LoginSerializer(TokenObtainPairSerializer):
    default_error_messages = {"no_active_account": "نام کاربری یا رمز عبور نادرست است."}

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSummarySerializer(self.user).data
        record_audit(action="auth.login", actor=self.user, request=self.context.get("request"))
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
