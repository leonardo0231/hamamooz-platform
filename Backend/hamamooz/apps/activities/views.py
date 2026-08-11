from rest_framework.exceptions import PermissionDenied

from hamamooz.apps.accounts.access import allowed_class_ids_for_roles, selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import Activity, ActivityAchievement, ActivityAttachment, ActivityParticipation
from .permissions import ACTIVITY_MANAGERS, ACTIVITY_WRITERS
from .serializers import (
    ActivityAchievementSerializer,
    ActivityAttachmentSerializer,
    ActivityParticipationSerializer,
    ActivitySerializer,
)


class ActivityViewSet(AuditedModelViewSet):
    queryset = Activity.objects.none()
    serializer_class = ActivitySerializer
    filterset_fields = ["organization", "school", "academic_year", "kind", "status"]
    search_fields = ["title", "description"]
    ordering_fields = ["starts_at", "created_at", "title"]
    required_roles_by_action = {
        "create": ACTIVITY_WRITERS,
        "update": ACTIVITY_MANAGERS,
        "partial_update": ACTIVITY_MANAGERS,
        "destroy": ACTIVITY_MANAGERS,
    }

    def get_queryset(self):
        return Activity.objects.filter(
            school_id__in=selected_school_ids(self.request)
        ).select_related("organization", "school", "academic_year", "created_by")

    def perform_create(self, serializer):
        self.perform_audited_create(
            serializer,
            action="activity.created",
            created_by=self.request.user,
        )

    def perform_update(self, serializer):
        if serializer.instance.status == Activity.Status.COMPLETED:
            raise PermissionDenied("A completed activity is immutable.")
        super().perform_update(serializer)


class ScopedActivityChildViewSet(AuditedModelViewSet):
    required_roles_by_action = {
        action_name: ACTIVITY_WRITERS
        for action_name in ["create", "update", "partial_update", "destroy"]
    }

    def activity_scope_queryset(self):
        return {"activity__school_id__in": selected_school_ids(self.request)}


class ActivityParticipationViewSet(ScopedActivityChildViewSet):
    queryset = ActivityParticipation.objects.none()
    serializer_class = ActivityParticipationSerializer
    filterset_fields = ["activity", "enrollment", "status"]
    ordering_fields = ["created_at", "placement"]

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids_for_roles(
            self.request.user, school_ids, [Role.STUDENT_AFFAIRS_DEPUTY]
        )
        return ActivityParticipation.objects.filter(
            activity__school_id__in=school_ids,
            enrollment__class_section_id__in=class_ids,
        ).select_related("activity", "enrollment__student", "enrollment__class_section")


class ActivityAchievementViewSet(AuditedModelViewSet):
    queryset = ActivityAchievement.objects.none()
    serializer_class = ActivityAchievementSerializer
    filterset_fields = ["participation"]
    ordering_fields = ["awarded_at", "created_at", "placement"]
    required_roles_by_action = {
        action_name: ACTIVITY_WRITERS
        for action_name in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids_for_roles(
            self.request.user, school_ids, [Role.STUDENT_AFFAIRS_DEPUTY]
        )
        return ActivityAchievement.objects.filter(
            participation__activity__school_id__in=school_ids,
            participation__enrollment__class_section_id__in=class_ids,
        ).select_related("participation__activity", "participation__enrollment__student")


class ActivityAttachmentViewSet(ScopedActivityChildViewSet):
    queryset = ActivityAttachment.objects.none()
    serializer_class = ActivityAttachmentSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["activity"]
    required_roles_by_action = {"create": ACTIVITY_WRITERS}

    def get_queryset(self):
        return ActivityAttachment.objects.filter(**self.activity_scope_queryset()).select_related(
            "activity", "uploaded_by"
        )
