from rest_framework.exceptions import PermissionDenied

from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import GuideActionPlan, GuideFollowUp, GuideTeacherAssignment
from .permissions import (
    GUIDANCE_MANAGEMENT_ROLES,
    GUIDANCE_WRITE_ROLES,
    can_write_assignment_data,
    guide_assignment_queryset,
)
from .serializers import (
    GuideActionPlanSerializer,
    GuideFollowUpSerializer,
    GuideTeacherAssignmentSerializer,
)


class GuideTeacherAssignmentViewSet(AuditedModelViewSet):
    queryset = GuideTeacherAssignment.objects.none()
    serializer_class = GuideTeacherAssignmentSerializer
    filterset_fields = ["enrollment", "guide_teacher"]
    required_roles_by_action = {
        action: GUIDANCE_MANAGEMENT_ROLES
        for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return guide_assignment_queryset(self.request).select_related(
            "enrollment__student", "guide_teacher", "assigned_by"
        )

    def perform_create(self, serializer):
        self.perform_audited_create(
            serializer, action="guidance.assignment_created", assigned_by=self.request.user
        )


class ScopedGuidanceChildViewSet(AuditedModelViewSet):
    required_roles_by_action = {
        action: GUIDANCE_WRITE_ROLES for action in ["create", "update", "partial_update", "destroy"]
    }

    def assignment_scope_queryset(self):
        return {"assignment__in": guide_assignment_queryset(self.request)}

    def perform_update(self, serializer):
        if not can_write_assignment_data(self.request, serializer.instance.assignment):
            raise PermissionDenied("You cannot modify this guidance record.")
        super().perform_update(serializer)


class GuideFollowUpViewSet(ScopedGuidanceChildViewSet):
    queryset = GuideFollowUp.objects.none()
    serializer_class = GuideFollowUpSerializer
    filterset_fields = ["assignment", "status"]
    ordering_fields = ["due_at", "created_at"]

    def get_queryset(self):
        return GuideFollowUp.objects.filter(**self.assignment_scope_queryset()).select_related(
            "assignment__enrollment__student", "created_by"
        )

    def perform_create(self, serializer):
        self.perform_audited_create(
            serializer, action="guidance.follow_up_created", created_by=self.request.user
        )


class GuideActionPlanViewSet(ScopedGuidanceChildViewSet):
    queryset = GuideActionPlan.objects.none()
    serializer_class = GuideActionPlanSerializer
    filterset_fields = ["assignment", "visibility"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return GuideActionPlan.objects.filter(**self.assignment_scope_queryset()).select_related(
            "assignment__enrollment__student", "created_by"
        )

    def perform_create(self, serializer):
        self.perform_audited_create(
            serializer, action="guidance.action_plan_created", created_by=self.request.user
        )
