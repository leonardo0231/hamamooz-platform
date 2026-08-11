from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Recommendation, RecommendationDecision
from .rules import RECOMMENDATION_RULES

TRANSITIONS = {
    Recommendation.Status.DRAFT: {
        Recommendation.Status.PENDING_REVIEW,
        Recommendation.Status.SUPERSEDED,
    },
    Recommendation.Status.PENDING_REVIEW: {
        Recommendation.Status.APPROVED,
        Recommendation.Status.REJECTED,
    },
    Recommendation.Status.APPROVED: {
        Recommendation.Status.DISMISSED,
        Recommendation.Status.EXPIRED,
        Recommendation.Status.SUPERSEDED,
    },
    Recommendation.Status.REJECTED: {Recommendation.Status.SUPERSEDED},
    Recommendation.Status.DISMISSED: set(),
    Recommendation.Status.EXPIRED: set(),
    Recommendation.Status.SUPERSEDED: set(),
}


def generate_recommendations_for_signal(*, signal):
    with transaction.atomic():
        generated = []
        for rule in RECOMMENDATION_RULES:
            for draft in rule.drafts_for(signal):
                recommendation, created = Recommendation.objects.get_or_create(
                    source_signal=signal,
                    audience=draft.audience,
                    rule_code=rule.code,
                    rule_version=rule.version,
                    status=Recommendation.Status.DRAFT,
                    defaults={
                        "organization": signal.organization,
                        "school": signal.school,
                        "enrollment": signal.enrollment,
                        "priority": draft.priority,
                        "reason_snapshot": draft.reason_snapshot,
                        "generated_text": draft.generated_text,
                    },
                )
                generated.append(recommendation)
        return generated


def transition_recommendation(
    *, recommendation, target_status, actor, approved_text="", rationale=""
):
    with transaction.atomic():
        locked = Recommendation.objects.select_for_update().get(pk=recommendation.pk)
        if target_status not in TRANSITIONS[locked.status]:
            raise ValidationError(
                {"target_status": "This recommendation transition is not allowed."}
            )
        if target_status == Recommendation.Status.APPROVED and not approved_text:
            raise ValidationError(
                {"approved_text": "Approval requires the reviewed recommendation text."}
            )
        old_status = locked.status
        locked.status = target_status
        update_fields = ["status", "updated_at"]
        if target_status == Recommendation.Status.APPROVED:
            locked.approved_text = approved_text
            locked.approved_at = timezone.now()
            locked.reviewer = actor
            update_fields.extend(["approved_text", "approved_at", "reviewer"])
        locked.full_clean(exclude=["id"])
        locked.save(update_fields=update_fields)
        RecommendationDecision.objects.create(
            recommendation=locked,
            actor=actor,
            from_status=old_status,
            to_status=target_status,
            rationale=rationale,
        )
        return locked
