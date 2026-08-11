from rest_framework import serializers

from hamamooz.apps.accounts.access import (
    accessible_organization_ids,
    allowed_class_ids_for_roles,
    selected_school_ids,
)
from hamamooz.apps.accounts.models import Role

from .models import (
    BehaviorAction,
    BehaviorAttachment,
    BehaviorEvent,
    BehaviorEventRevision,
    BehaviorEventType,
    BehaviorFollowUp,
)


def validate_event_scope(*, event, request):
    school_ids = selected_school_ids(request)
    class_ids = allowed_class_ids_for_roles(request.user, school_ids, [Role.STUDENT_AFFAIRS_DEPUTY])
    if event.school_id not in set(school_ids) or event.enrollment.class_section_id not in set(
        class_ids
    ):
        raise serializers.ValidationError("The event is outside the selected access scope.")
    return event


class BehaviorEventTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehaviorEventType
        fields = [
            "id",
            "organization",
            "code",
            "title",
            "default_polarity",
            "default_severity",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_organization(self, value):
        request = self.context.get("request")
        if request and value.id not in set(accessible_organization_ids(request.user)):
            raise serializers.ValidationError("You do not have access to this organization.")
        return value


class BehaviorEventRevisionSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True)

    class Meta:
        model = BehaviorEventRevision
        fields = [
            "id",
            "actor",
            "actor_name",
            "reason",
            "changed_fields",
            "previous_occurred_at",
            "created_at",
        ]
        read_only_fields = fields


class BehaviorEventSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)
    class_title = serializers.CharField(source="enrollment.class_section.title", read_only=True)
    event_type_title = serializers.CharField(source="event_type.title", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)
    confirmed_by_name = serializers.CharField(source="confirmed_by.get_full_name", read_only=True)
    revisions = BehaviorEventRevisionSerializer(many=True, read_only=True)

    class Meta:
        model = BehaviorEvent
        fields = [
            "id",
            "organization",
            "school",
            "academic_year",
            "enrollment",
            "student_name",
            "class_title",
            "event_type",
            "event_type_title",
            "polarity",
            "severity",
            "occurred_at",
            "description",
            "status",
            "recorded_by",
            "recorded_by_name",
            "confirmed_by",
            "confirmed_by_name",
            "confirmed_at",
            "voided_by",
            "void_reason",
            "revisions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student_name",
            "class_title",
            "event_type_title",
            "status",
            "recorded_by",
            "recorded_by_name",
            "confirmed_by",
            "confirmed_by_name",
            "confirmed_at",
            "voided_by",
            "void_reason",
            "revisions",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        if self.instance:
            immutable = {"organization", "school", "academic_year", "enrollment", "event_type"}
            changed = {
                field
                for field in immutable
                if field in attrs and attrs[field] != getattr(self.instance, field)
            }
            if changed:
                raise serializers.ValidationError(
                    "Organization, school, academic year, enrollment, and event type are immutable."
                )
        event = self.instance or BehaviorEvent(recorded_by=getattr(request, "user", None))
        for field, value in attrs.items():
            setattr(event, field, value)
        if request:
            validate_event_scope(event=event, request=request)
        event.full_clean(exclude=["id"])
        return attrs


class BehaviorEventTransitionSerializer(serializers.Serializer):
    target_status = serializers.ChoiceField(choices=BehaviorEvent.Status.choices)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class BehaviorEventRevisionInputSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, max_length=500)
    description = serializers.CharField(required=False, allow_blank=False)
    occurred_at = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        if "description" not in attrs and "occurred_at" not in attrs:
            raise serializers.ValidationError(
                "Provide a description or occurred_at value to revise."
            )
        return attrs


class BehaviorActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehaviorAction
        fields = [
            "id",
            "event",
            "title",
            "description",
            "assigned_to",
            "due_at",
            "status",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_event(self, value):
        request = self.context.get("request")
        if request:
            validate_event_scope(event=value, request=request)
        return value


class BehaviorFollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehaviorFollowUp
        fields = [
            "id",
            "event",
            "due_at",
            "note",
            "status",
            "completed_by",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_event(self, value):
        request = self.context.get("request")
        if request:
            validate_event_scope(event=value, request=request)
        return value


class BehaviorAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehaviorAttachment
        fields = ["id", "event", "file", "original_name", "uploaded_by", "created_at", "updated_at"]
        read_only_fields = ["id", "original_name", "uploaded_by", "created_at", "updated_at"]

    def validate_event(self, value):
        request = self.context.get("request")
        if request:
            validate_event_scope(event=value, request=request)
        return value

    def create(self, validated_data):
        uploaded_file = validated_data["file"]
        return BehaviorAttachment.objects.create(
            original_name=uploaded_file.name,
            uploaded_by=self.context["request"].user,
            **validated_data,
        )
