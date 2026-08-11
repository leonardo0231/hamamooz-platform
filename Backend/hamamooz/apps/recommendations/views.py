from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from hamamooz.apps.accounts.access import allowed_class_ids_for_roles, selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.services import record_audit
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import Recommendation
from .permissions import (
    RECOMMENDATION_REVIEWERS,
    RECOMMENDATION_TRANSITION_CANDIDATES,
    can_transition_recommendation,
    visible_recommendations_queryset,
)
from .serializers import (
    GenerateRecommendationsSerializer,
    RecommendationSerializer,
    RecommendationTransitionSerializer,
)
from .services import generate_recommendations_for_signal, transition_recommendation


class RecommendationViewSet(AuditedModelViewSet):
    queryset = Recommendation.objects.none()
    serializer_class = RecommendationSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["school", "enrollment", "audience", "status", "priority", "rule_code"]
    ordering_fields = ["created_at", "approved_at", "priority"]
    required_roles_by_action = {
        "generate": RECOMMENDATION_REVIEWERS,
        "transition": RECOMMENDATION_TRANSITION_CANDIDATES,
    }

    def get_queryset(self):
        return (
            visible_recommendations_queryset(self.request)
            .select_related("enrollment__student", "source_signal", "reviewer")
            .prefetch_related("decisions")
        )

    @extend_schema(
        request=GenerateRecommendationsSerializer,
        responses={201: RecommendationSerializer(many=True)},
    )
    @action(detail=False, methods=["post"])
    def generate(self, request):
        serializer = GenerateRecommendationsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from hamamooz.apps.analytics.models import StudentRiskSignal

        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids_for_roles(
            request.user, school_ids, [Role.STUDENT_AFFAIRS_DEPUTY]
        )
        signal = StudentRiskSignal.objects.filter(
            pk=serializer.validated_data["signal"],
            school_id__in=school_ids,
            enrollment__class_section_id__in=class_ids,
            state=StudentRiskSignal.State.ACTIVE,
        ).first()
        if not signal:
            raise PermissionDenied("Signal is outside the selected recommendation scope.")
        generated = generate_recommendations_for_signal(signal=signal)
        for recommendation in generated:
            record_audit(
                action="recommendation.generated",
                actor=request.user,
                request=request,
                entity=recommendation,
                organization_id=recommendation.organization_id,
                school_id=recommendation.school_id,
                metadata={
                    "rule_code": recommendation.rule_code,
                    "rule_version": recommendation.rule_version,
                },
            )
        visible = self.get_queryset().filter(
            pk__in=[recommendation.pk for recommendation in generated]
        )
        return Response(RecommendationSerializer(visible, many=True).data, status=201)

    @extend_schema(
        request=RecommendationTransitionSerializer, responses={200: RecommendationSerializer}
    )
    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        recommendation = self.get_object()
        if not can_transition_recommendation(request.user, recommendation):
            raise PermissionDenied("Only an authorized reviewer may change recommendation state.")
        serializer = RecommendationTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = transition_recommendation(
            recommendation=recommendation,
            target_status=serializer.validated_data["target_status"],
            actor=request.user,
            approved_text=serializer.validated_data.get("approved_text", ""),
            rationale=serializer.validated_data.get("rationale", ""),
        )
        record_audit(
            action="recommendation.transitioned",
            actor=request.user,
            request=request,
            entity=updated,
            organization_id=updated.organization_id,
            school_id=updated.school_id,
            metadata={"target_status": updated.status},
        )
        return Response(RecommendationSerializer(updated).data)
