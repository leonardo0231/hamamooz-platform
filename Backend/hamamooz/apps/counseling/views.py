from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from hamamooz.apps.core.services import record_audit

from .models import (
    CounselingActionPlan,
    CounselingAttachment,
    CounselingCase,
    CounselingFollowUp,
    CounselingSession,
    Referral,
)
from .permissions import can_manage_shared_case, can_read_private_case, shared_case_queryset
from .serializers import (
    CounselingActionPlanSerializer,
    CounselingAttachmentInputSerializer,
    CounselingCaseCreateSerializer,
    CounselingCaseSharedSerializer,
    CounselingCaseTransitionSerializer,
    CounselingFollowUpSerializer,
    CounselingPrivateSessionInputSerializer,
    CounselingPrivateSessionSerializer,
    ReferralSerializer,
)
from .services import accept_referral, transition_case


class ConfidentialBaseViewSet(viewsets.ModelViewSet):
    """Audit without serializing or logging narrative fields.

    This deliberately does not inherit the normal role viewset: generic staff
    permissions and system-admin shortcuts are unsafe for counseling data.
    """

    permission_classes = [IsAuthenticated]

    def record_confidential_audit(self, *, action_name, entity, metadata=None):
        record_audit(
            action=action_name,
            actor=self.request.user,
            request=self.request,
            entity=entity,
            organization_id=entity.organization_id,
            school_id=entity.school_id,
            metadata=metadata or {},
        )


class CounselingCaseViewSet(ConfidentialBaseViewSet):
    queryset = CounselingCase.objects.none()
    filterset_fields = ["school", "enrollment", "status", "shared_risk_level"]
    ordering_fields = ["created_at", "opened_at", "closed_at"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return shared_case_queryset(self.request).select_related(
            "organization", "school", "enrollment__student", "assigned_counselor"
        )

    def get_serializer_class(self):
        return (
            CounselingCaseCreateSerializer
            if self.action == "create"
            else CounselingCaseSharedSerializer
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        school = serializer.validated_data["school"]
        # The case creator must personally be the counselor. A manager cannot
        # create a confidential case just by naming someone else as assignee.
        provisional = CounselingCase(school=school, assigned_counselor=request.user)
        if not can_read_private_case(request.user, provisional):
            raise PermissionDenied("Only a school counselor may open a counseling case.")
        with transaction.atomic():
            instance = CounselingCase.objects.create(
                **serializer.validated_data,
                assigned_counselor=request.user,
                opened_by=request.user,
            )
            self.record_confidential_audit(
                action_name="counseling.case_created",
                entity=instance,
                metadata={"scope": "case_metadata"},
            )
        return Response(
            CounselingCaseSharedSerializer(instance).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        request=CounselingCaseTransitionSerializer, responses={200: CounselingCaseSharedSerializer}
    )
    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        case = self.get_object()
        if not can_read_private_case(request.user, case):
            raise PermissionDenied("Only the assigned counselor may transition this case.")
        serializer = CounselingCaseTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = transition_case(
            case=case, target_status=serializer.validated_data["target_status"]
        )
        self.record_confidential_audit(
            action_name="counseling.case_transitioned",
            entity=updated,
            metadata={"scope": "case_metadata", "target_status": updated.status},
        )
        return Response(CounselingCaseSharedSerializer(updated).data)

    @extend_schema(
        request=CounselingPrivateSessionInputSerializer,
        responses={
            200: CounselingPrivateSessionSerializer(many=True),
            201: CounselingPrivateSessionSerializer,
        },
    )
    @action(detail=True, methods=["get", "post"], url_path="private-sessions")
    def private_sessions(self, request, pk=None):
        case = self.get_object()
        if not can_read_private_case(request.user, case):
            raise PermissionDenied(
                "Private counseling sessions are visible only to the assigned counselor."
            )
        if request.method == "GET":
            sessions = case.sessions.select_related("recorded_by").all()
            self.record_confidential_audit(
                action_name="counseling.private_sessions_read",
                entity=case,
                metadata={"scope": "private_sessions", "access_reason": "assigned_counselor"},
            )
            return Response(CounselingPrivateSessionSerializer(sessions, many=True).data)
        serializer = CounselingPrivateSessionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = CounselingSession.objects.create(
            case=case, recorded_by=request.user, **serializer.validated_data
        )
        self.record_confidential_audit(
            action_name="counseling.private_session_created",
            entity=session,
            metadata={"scope": "private_sessions"},
        )
        return Response(
            CounselingPrivateSessionSerializer(session).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(request=ReferralSerializer, responses={201: ReferralSerializer})
    @action(detail=True, methods=["get", "post"], url_path="referrals")
    def referrals(self, request, pk=None):
        case = self.get_object()
        if not can_read_private_case(request.user, case):
            raise PermissionDenied("Only the assigned counselor may access case referrals.")
        if request.method == "GET":
            return Response(ReferralSerializer(case.referrals.all(), many=True).data)
        serializer = ReferralSerializer(
            data=request.data, context={"request": request, "source_case": case}
        )
        serializer.is_valid(raise_exception=True)
        referral = Referral.objects.create(
            source_case=case,
            created_by=request.user,
            status=Referral.Status.SENT,
            **serializer.validated_data,
        )
        self.record_confidential_audit(
            action_name="counseling.referral_sent",
            entity=case,
            metadata={"scope": "referral", "referral_id": str(referral.id)},
        )
        return Response(ReferralSerializer(referral).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=CounselingAttachmentInputSerializer,
        responses={201: CounselingAttachmentInputSerializer},
    )
    @action(detail=True, methods=["post"], url_path="private-attachments")
    def private_attachments(self, request, pk=None):
        case = self.get_object()
        if not can_read_private_case(request.user, case):
            raise PermissionDenied(
                "Private counseling attachments are visible only to the assigned counselor."
            )
        serializer = CounselingAttachmentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded = serializer.validated_data["file"]
        attachment = CounselingAttachment.objects.create(
            case=case, file=uploaded, original_name=uploaded.name, uploaded_by=request.user
        )
        self.record_confidential_audit(
            action_name="counseling.private_attachment_created",
            entity=attachment,
            metadata={"scope": "private_attachments"},
        )
        return Response(
            {"id": str(attachment.id), "original_name": attachment.original_name},
            status=status.HTTP_201_CREATED,
        )


class CounselingFollowUpViewSet(ConfidentialBaseViewSet):
    queryset = CounselingFollowUp.objects.none()
    serializer_class = CounselingFollowUpSerializer
    filterset_fields = ["case", "status"]
    ordering_fields = ["due_at", "created_at"]

    def get_queryset(self):
        return CounselingFollowUp.objects.filter(
            case__in=shared_case_queryset(self.request)
        ).select_related("case", "created_by")

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        self.record_confidential_audit(
            action_name="counseling.follow_up_created",
            entity=instance,
            metadata={"scope": "shared_follow_up"},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        self.record_confidential_audit(
            action_name="counseling.follow_up_updated",
            entity=instance,
            metadata={"scope": "shared_follow_up"},
        )

    def perform_destroy(self, instance):
        if not can_manage_shared_case(self.request.user, instance.case):
            raise PermissionDenied("You cannot delete this counseling follow-up.")
        self.record_confidential_audit(
            action_name="counseling.follow_up_deleted",
            entity=instance,
            metadata={"scope": "shared_follow_up"},
        )
        instance.delete()


class CounselingActionPlanViewSet(ConfidentialBaseViewSet):
    queryset = CounselingActionPlan.objects.none()
    serializer_class = CounselingActionPlanSerializer
    filterset_fields = ["case", "visibility"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return CounselingActionPlan.objects.filter(
            case__in=shared_case_queryset(self.request)
        ).select_related("case", "created_by")

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        self.record_confidential_audit(
            action_name="counseling.action_plan_created",
            entity=instance,
            metadata={"scope": "action_plan"},
        )

    def perform_update(self, serializer):
        if not can_read_private_case(self.request.user, serializer.instance.case):
            raise PermissionDenied("Only the assigned counselor may modify an action plan.")
        instance = serializer.save()
        self.record_confidential_audit(
            action_name="counseling.action_plan_updated",
            entity=instance,
            metadata={"scope": "action_plan"},
        )


class CounselingReferralViewSet(ConfidentialBaseViewSet):
    """Inbox for explicitly handed-off cases; it never exposes source sessions."""

    queryset = Referral.objects.none()
    serializer_class = ReferralSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["status"]

    def get_queryset(self):
        return Referral.objects.filter(target_counselor=self.request.user).select_related(
            "source_case", "target_enrollment__school", "accepted_case"
        )

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        referral = self.get_object()
        accepted = accept_referral(referral=referral, actor=request.user)
        self.record_confidential_audit(
            action_name="counseling.referral_accepted",
            entity=accepted.accepted_case,
            metadata={"scope": "referral", "referral_id": str(accepted.id)},
        )
        return Response(ReferralSerializer(accepted).data)
