from rest_framework import serializers

from hamamooz.apps.accounts.access import (
    accessible_organization_ids,
    allowed_class_ids_for_roles,
    selected_school_ids,
)
from hamamooz.apps.accounts.models import Role

from .models import Activity, ActivityAchievement, ActivityAttachment, ActivityParticipation


def validate_activity_scope(*, activity, request):
    school_ids = selected_school_ids(request)
    if activity.school_id not in set(school_ids):
        raise serializers.ValidationError("The activity is outside the selected access scope.")
    return activity


def validate_participation_scope(*, participation, request):
    validate_activity_scope(activity=participation.activity, request=request)
    class_ids = allowed_class_ids_for_roles(
        request.user,
        [participation.activity.school_id],
        [Role.STUDENT_AFFAIRS_DEPUTY],
    )
    if participation.enrollment.class_section_id not in set(class_ids):
        raise serializers.ValidationError("The participation is outside the selected class scope.")
    return participation


class ActivitySerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source="school.name", read_only=True)
    academic_year_title = serializers.CharField(source="academic_year.title", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = Activity
        fields = [
            "id",
            "organization",
            "school",
            "school_name",
            "academic_year",
            "academic_year_title",
            "title",
            "kind",
            "description",
            "starts_at",
            "ends_at",
            "status",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "school_name",
            "academic_year_title",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        if self.instance:
            immutable = {"organization", "school", "academic_year"}
            changed = {
                field
                for field in immutable
                if field in attrs and attrs[field] != getattr(self.instance, field)
            }
            if changed:
                raise serializers.ValidationError(
                    "Organization, school, and academic year are immutable after creation."
                )
        activity = self.instance or Activity(created_by=getattr(request, "user", None))
        for field, value in attrs.items():
            setattr(activity, field, value)
        if request:
            validate_activity_scope(activity=activity, request=request)
            if activity.organization_id not in set(accessible_organization_ids(request.user)):
                raise serializers.ValidationError(
                    {"organization": "Organization is not accessible."}
                )
        activity.full_clean(exclude=["id"])
        return attrs


class ActivityParticipationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)
    activity_title = serializers.CharField(source="activity.title", read_only=True)

    class Meta:
        model = ActivityParticipation
        fields = [
            "id",
            "activity",
            "activity_title",
            "enrollment",
            "student_name",
            "status",
            "participation_role",
            "result",
            "placement",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "activity_title", "student_name", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        instance = self.instance or ActivityParticipation()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean(exclude=["id"])
        if request:
            validate_participation_scope(participation=instance, request=request)
        return attrs


class ActivityAchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityAchievement
        fields = [
            "id",
            "participation",
            "title",
            "result",
            "placement",
            "awarded_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_participation(self, value):
        request = self.context.get("request")
        if request:
            validate_participation_scope(participation=value, request=request)
        return value


class ActivityAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityAttachment
        fields = [
            "id",
            "activity",
            "file",
            "original_name",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "original_name", "uploaded_by", "created_at", "updated_at"]

    def validate_activity(self, value):
        request = self.context.get("request")
        if request:
            validate_activity_scope(activity=value, request=request)
        return value

    def create(self, validated_data):
        uploaded_file = validated_data["file"]
        return ActivityAttachment.objects.create(
            original_name=uploaded_file.name,
            uploaded_by=self.context["request"].user,
            **validated_data,
        )
