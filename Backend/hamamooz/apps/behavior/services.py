from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import BehaviorEvent, BehaviorEventRevision

ALLOWED_TRANSITIONS = {
    BehaviorEvent.Status.DRAFT: {
        BehaviorEvent.Status.CONFIRMED,
        BehaviorEvent.Status.VOIDED,
    },
    BehaviorEvent.Status.CONFIRMED: {
        BehaviorEvent.Status.UNDER_FOLLOW_UP,
        BehaviorEvent.Status.VOIDED,
    },
    BehaviorEvent.Status.UNDER_FOLLOW_UP: {BehaviorEvent.Status.RESOLVED},
    BehaviorEvent.Status.RESOLVED: set(),
    BehaviorEvent.Status.VOIDED: set(),
}


@transaction.atomic
def transition_event(*, event, target_status, actor, reason=""):
    locked = BehaviorEvent.objects.select_for_update().get(pk=event.pk)
    if target_status not in ALLOWED_TRANSITIONS[locked.status]:
        raise ValidationError({"target_status": "This state transition is not allowed."})
    if target_status == BehaviorEvent.Status.VOIDED and not reason.strip():
        raise ValidationError({"reason": "Voiding an event requires a reason."})
    locked.status = target_status
    update_fields = ["status", "updated_at"]
    if target_status == BehaviorEvent.Status.CONFIRMED:
        locked.confirmed_by = actor
        locked.confirmed_at = timezone.now()
        update_fields.extend(["confirmed_by", "confirmed_at"])
    if target_status == BehaviorEvent.Status.VOIDED:
        locked.voided_by = actor
        locked.void_reason = reason.strip()
        update_fields.extend(["voided_by", "void_reason"])
    locked.full_clean()
    locked.save(update_fields=update_fields)
    if target_status in {
        BehaviorEvent.Status.CONFIRMED,
        BehaviorEvent.Status.UNDER_FOLLOW_UP,
        BehaviorEvent.Status.RESOLVED,
    }:
        from hamamooz.apps.analytics.scheduling import schedule_targeted_analytics

        schedule_targeted_analytics([locked.enrollment_id])
    return locked


@transaction.atomic
def revise_confirmed_event(*, event, actor, reason, description=None, occurred_at=None):
    locked = BehaviorEvent.objects.select_for_update().get(pk=event.pk)
    if locked.status not in {
        BehaviorEvent.Status.CONFIRMED,
        BehaviorEvent.Status.UNDER_FOLLOW_UP,
        BehaviorEvent.Status.RESOLVED,
    }:
        raise ValidationError({"detail": "Only confirmed events can be revised."})
    changed_fields = []
    if description is not None and description != locked.description:
        changed_fields.append("description")
    if occurred_at is not None and occurred_at != locked.occurred_at:
        changed_fields.append("occurred_at")
    if not changed_fields:
        raise ValidationError({"detail": "The revision contains no changes."})
    BehaviorEventRevision.objects.create(
        event=locked,
        actor=actor,
        reason=reason,
        changed_fields=changed_fields,
        previous_occurred_at=locked.occurred_at,
        previous_description_digest=BehaviorEventRevision.description_digest(locked.description),
    )
    if description is not None:
        locked.description = description
    if occurred_at is not None:
        locked.occurred_at = occurred_at
    locked.full_clean()
    locked.save(update_fields=[*changed_fields, "updated_at"])
    return locked
