from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from hamamooz.apps.accounts.access import (
    accessible_organization_ids,
    allowed_class_ids_for_roles,
    selected_school_ids,
)
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.services import record_audit
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import (
    BehaviorAction,
    BehaviorAttachment,
    BehaviorEvent,
    BehaviorEventType,
    BehaviorFollowUp,
)
from .permissions import BEHAVIOR_RECORDERS, BEHAVIOR_REVIEWERS
from .serializers import (
    BehaviorActionSerializer,
    BehaviorAttachmentSerializer,
    BehaviorEventRevisionInputSerializer,
    BehaviorEventSerializer,
    BehaviorEventTransitionSerializer,
    BehaviorEventTypeSerializer,
    BehaviorFollowUpSerializer,
)
from .services import revise_confirmed_event, transition_event


class BehaviorEventTypeViewSet(AuditedModelViewSet):
    queryset = BehaviorEventType.objects.none()
    serializer_class = BehaviorEventTypeSerializer
    filterset_fields = ["organization", "is_active"]
    search_fields = ["code", "title"]
    required_roles_by_action = {
        action_name: BEHAVIOR_REVIEWERS
        for action_name in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return BehaviorEventType.objects.filter(
            organization_id__in=accessible_organization_ids(self.request.user)
        )


class BehaviorEventViewSet(AuditedModelViewSet):
    queryset = BehaviorEvent.objects.none()
    serializer_class = BehaviorEventSerializer
    filterset_fields = [
        "organization",
        "school",
        "academic_year",
        "enrollment",
        "event_type",
        "polarity",
        "severity",
        "status",
    ]
    search_fields = [
        "enrollment__student__first_name",
        "enrollment__student__last_name",
        "description",
    ]
    ordering_fields = ["occurred_at", "created_at", "severity"]
    required_roles_by_action = {
        "create": BEHAVIOR_RECORDERS,
        "partial_update": BEHAVIOR_RECORDERS,
        "update": BEHAVIOR_RECORDERS,
        "destroy": BEHAVIOR_REVIEWERS,
        "transition": BEHAVIOR_REVIEWERS,
        "revise": BEHAVIOR_REVIEWERS,
    }

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids_for_roles(
            self.request.user, school_ids, [Role.STUDENT_AFFAIRS_DEPUTY]
        )
        return (
            BehaviorEvent.objects.filter(
                school_id__in=school_ids,
                enrollment__class_section_id__in=class_ids,
            )
            .select_related(
                "organization",
                "school",
                "academic_year",
                "enrollment__student",
                "enrollment__class_section",
                "event_type",
                "recorded_by",
                "confirmed_by",
                "voided_by",
            )
            .prefetch_related("revisions__actor")
        )

    def perform_create(self, serializer):
        self.perform_audited_create(
            serializer,
            action="behavior.event_recorded",
            recorded_by=self.request.user,
        )

    def perform_update(self, serializer):
        if serializer.instance.status != BehaviorEvent.Status.DRAFT:
            raise PermissionDenied("Only draft behavior events may be updated directly.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.status != BehaviorEvent.Status.DRAFT:
            raise PermissionDenied("Only draft behavior events may be deleted.")
        super().perform_destroy(instance)

    @extend_schema(
        request=BehaviorEventTransitionSerializer, responses={200: BehaviorEventSerializer}
    )
    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        event = self.get_object()
        serializer = BehaviorEventTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous_status = event.status
        updated = transition_event(
            event=event,
            target_status=serializer.validated_data["target_status"],
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )
        record_audit(
            action="behavior.event_transitioned",
            actor=request.user,
            request=request,
            entity=updated,
            organization_id=updated.organization_id,
            school_id=updated.school_id,
            changes={"from_status": previous_status, "to_status": updated.status},
        )
        return Response(BehaviorEventSerializer(self.get_queryset().get(pk=updated.pk)).data)

    @extend_schema(
        request=BehaviorEventRevisionInputSerializer, responses={200: BehaviorEventSerializer}
    )
    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        event = self.get_object()
        serializer = BehaviorEventRevisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = revise_confirmed_event(
            event=event,
            actor=request.user,
            reason=serializer.validated_data["reason"],
            description=serializer.validated_data.get("description"),
            occurred_at=serializer.validated_data.get("occurred_at"),
        )
        record_audit(
            action="behavior.event_revised",
            actor=request.user,
            request=request,
            entity=updated,
            organization_id=updated.organization_id,
            school_id=updated.school_id,
            metadata={"changed_fields": list(updated.revisions.first().changed_fields)},
        )
        return Response(BehaviorEventSerializer(self.get_queryset().get(pk=updated.pk)).data)


class ScopedBehaviorChildViewSet(AuditedModelViewSet):
    required_roles_by_action = {
        action_name: BEHAVIOR_RECORDERS
        for action_name in ["create", "update", "partial_update", "destroy"]
    }

    def event_scope_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids_for_roles(
            self.request.user, school_ids, [Role.STUDENT_AFFAIRS_DEPUTY]
        )
        return {
            "event__school_id__in": school_ids,
            "event__enrollment__class_section_id__in": class_ids,
        }


class BehaviorActionViewSet(ScopedBehaviorChildViewSet):
    queryset = BehaviorAction.objects.none()
    serializer_class = BehaviorActionSerializer
    filterset_fields = ["event", "status", "assigned_to"]
    ordering_fields = ["due_at", "created_at"]

    def get_queryset(self):
        return BehaviorAction.objects.filter(**self.event_scope_queryset()).select_related(
            "event", "assigned_to"
        )


class BehaviorFollowUpViewSet(ScopedBehaviorChildViewSet):
    queryset = BehaviorFollowUp.objects.none()
    serializer_class = BehaviorFollowUpSerializer
    filterset_fields = ["event", "status"]
    ordering_fields = ["due_at", "created_at"]

    def get_queryset(self):
        return BehaviorFollowUp.objects.filter(**self.event_scope_queryset()).select_related(
            "event", "completed_by"
        )


class BehaviorAttachmentViewSet(ScopedBehaviorChildViewSet):
    queryset = BehaviorAttachment.objects.none()
    serializer_class = BehaviorAttachmentSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["event"]
    required_roles_by_action = {"create": BEHAVIOR_RECORDERS}

    def get_queryset(self):
        return BehaviorAttachment.objects.filter(**self.event_scope_queryset()).select_related(
            "event", "uploaded_by"
        )
