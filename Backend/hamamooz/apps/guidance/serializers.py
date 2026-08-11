from django.utils import timezone
from rest_framework import serializers

from hamamooz.apps.accounts.access import selected_school_ids
from hamamooz.apps.accounts.models import Role, RoleAssignment

from .models import GuideActionPlan, GuideFollowUp, GuideTeacherAssignment
from .permissions import can_write_assignment_data, guide_assignment_queryset


class GuideTeacherAssignmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)

    class Meta:
        model = GuideTeacherAssignment
        fields = [
            "id",
            "enrollment",
            "student_name",
            "guide_teacher",
            "starts_at",
            "ends_at",
            "assigned_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "student_name", "assigned_by", "created_at", "updated_at"]

    def validate_enrollment(self, enrollment):
        request = self.context["request"]
        if enrollment.school_id not in set(selected_school_ids(request)):
            raise serializers.ValidationError("Enrollment is outside the selected school scope.")
        return enrollment

    def validate(self, attrs):
        instance = self.instance or GuideTeacherAssignment(assigned_by=self.context["request"].user)
        for field, value in attrs.items():
            setattr(instance, field, value)
        if not RoleAssignment.objects.filter(
            user=instance.guide_teacher,
            organization_id=instance.enrollment.school.organization_id,
            school_id=instance.enrollment.school_id,
            role=Role.GUIDE_TEACHER,
            is_active=True,
            is_deleted=False,
        ).exists():
            raise serializers.ValidationError(
                {
                    "guide_teacher": "The assigned user must hold an active guide-teacher role in this school."
                }
            )
        instance.full_clean(exclude=["id"])
        return attrs


class GuideFollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuideFollowUp
        fields = [
            "id",
            "assignment",
            "title",
            "due_at",
            "status",
            "note",
            "completed_at",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def validate_assignment(self, assignment):
        if not guide_assignment_queryset(self.context["request"]).filter(pk=assignment.pk).exists():
            raise serializers.ValidationError("Assignment is outside your guidance cohort.")
        return assignment

    def validate(self, attrs):
        request = self.context["request"]
        assignment = attrs.get("assignment") or self.instance.assignment
        if not can_write_assignment_data(request, assignment):
            raise serializers.ValidationError("You cannot update this assignment.")
        if attrs.get("status") == GuideFollowUp.Status.COMPLETED and not attrs.get("completed_at"):
            attrs["completed_at"] = timezone.now()
        return attrs


class GuideActionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuideActionPlan
        fields = [
            "id",
            "assignment",
            "title",
            "objectives",
            "visibility",
            "released_at",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def validate_assignment(self, assignment):
        if not guide_assignment_queryset(self.context["request"]).filter(pk=assignment.pk).exists():
            raise serializers.ValidationError("Assignment is outside your guidance cohort.")
        return assignment

    def validate(self, attrs):
        request = self.context["request"]
        assignment = attrs.get("assignment") or self.instance.assignment
        if not can_write_assignment_data(request, assignment):
            raise serializers.ValidationError("You cannot update this assignment.")
        if attrs.get("visibility") == GuideActionPlan.Visibility.RELEASED and not attrs.get(
            "released_at"
        ):
            attrs["released_at"] = timezone.now()
        instance = self.instance or GuideActionPlan(created_by=request.user)
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean(exclude=["id"])
        return attrs
