from rest_framework import serializers

from hamamooz.apps.accounts.access import selected_school_ids
from hamamooz.apps.accounts.models import Role, RoleAssignment

from .models import (
    CounselingActionPlan,
    CounselingCase,
    CounselingFollowUp,
    CounselingSession,
    Referral,
)
from .permissions import can_manage_shared_case, can_read_private_case, shared_case_queryset


class CounselingCaseSharedSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)

    class Meta:
        model = CounselingCase
        fields = [
            "id",
            "organization",
            "school",
            "enrollment",
            "student_name",
            "assigned_counselor",
            "status",
            "shared_risk_level",
            "shared_follow_up_status",
            "opened_at",
            "closed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CounselingCaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CounselingCase
        fields = [
            "organization",
            "school",
            "enrollment",
            "assigned_counselor",
            "shared_risk_level",
            "shared_follow_up_status",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        school = attrs["school"]
        if school.id not in set(selected_school_ids(request)):
            raise serializers.ValidationError(
                {"school": "School is outside the selected access scope."}
            )
        if attrs["organization"].id != school.organization_id:
            raise serializers.ValidationError(
                {"organization": "Organization must own the selected school."}
            )
        if attrs["enrollment"].school_id != school.id:
            raise serializers.ValidationError(
                {"enrollment": "Enrollment must belong to the selected school."}
            )
        if not RoleAssignment.objects.filter(
            user=attrs["assigned_counselor"],
            role=Role.COUNSELOR,
            school=school,
            is_active=True,
            is_deleted=False,
        ).exists():
            raise serializers.ValidationError(
                {"assigned_counselor": "The assignee must be a counselor for this school."}
            )
        if attrs["assigned_counselor"].id != request.user.id:
            raise serializers.ValidationError(
                {"assigned_counselor": "A counselor may open only a case assigned to themself."}
            )
        return attrs


class CounselingCaseTransitionSerializer(serializers.Serializer):
    target_status = serializers.ChoiceField(
        choices=[choice for choice, _ in CounselingCase.Status.choices]
    )


class CounselingPrivateSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CounselingSession
        fields = ["id", "occurred_at", "private_note", "recorded_by", "created_at"]
        read_only_fields = ["id", "recorded_by", "created_at"]


class CounselingPrivateSessionInputSerializer(serializers.Serializer):
    occurred_at = serializers.DateTimeField()
    private_note = serializers.CharField(allow_blank=False, trim_whitespace=False)


class CounselingFollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = CounselingFollowUp
        fields = [
            "id",
            "case",
            "title",
            "due_at",
            "status",
            "shared_note",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def validate_case(self, value):
        request = self.context["request"]
        if not shared_case_queryset(request).filter(pk=value.pk).exists():
            raise serializers.ValidationError("Case is outside your counseling scope.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        case = attrs.get("case") or self.instance.case
        if not can_manage_shared_case(request.user, case):
            raise serializers.ValidationError("You cannot write this counseling follow-up.")
        return attrs


class CounselingActionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = CounselingActionPlan
        fields = [
            "id",
            "case",
            "title",
            "guidance",
            "visibility",
            "released_at",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def validate_case(self, value):
        request = self.context["request"]
        if not shared_case_queryset(request).filter(pk=value.pk).exists():
            raise serializers.ValidationError("Case is outside your counseling scope.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        case = attrs.get("case") or self.instance.case
        if not can_read_private_case(request.user, case):
            raise serializers.ValidationError(
                "Only the assigned counselor may write an action plan."
            )
        if attrs.get("visibility") == CounselingActionPlan.Visibility.RELEASED and not attrs.get(
            "released_at"
        ):
            from django.utils import timezone

            attrs["released_at"] = timezone.now()
        return attrs


class ReferralSerializer(serializers.ModelSerializer):
    source_case_id = serializers.UUIDField(source="source_case.id", read_only=True)
    accepted_case_id = serializers.UUIDField(
        source="accepted_case.id", read_only=True, allow_null=True
    )

    class Meta:
        model = Referral
        fields = [
            "id",
            "source_case_id",
            "target_enrollment",
            "target_counselor",
            "purpose",
            "handoff_summary",
            "status",
            "accepted_case_id",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "accepted_case_id",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        source_case = self.context.get("source_case")
        if source_case is None:
            raise serializers.ValidationError("A source counseling case is required.")
        target = attrs["target_enrollment"]
        if target.student_id != source_case.enrollment.student_id:
            raise serializers.ValidationError(
                {"target_enrollment": "A referral must target the same student."}
            )
        if not RoleAssignment.objects.filter(
            user=attrs["target_counselor"],
            role=Role.COUNSELOR,
            school=target.school,
            is_active=True,
            is_deleted=False,
        ).exists():
            raise serializers.ValidationError(
                {"target_counselor": "The target must be a counselor at the target school."}
            )
        if not can_read_private_case(request.user, source_case):
            raise serializers.ValidationError("Only the assigned counselor may refer a case.")
        return attrs


class CounselingAttachmentInputSerializer(serializers.Serializer):
    file = serializers.FileField()
