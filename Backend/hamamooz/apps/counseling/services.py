from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import CounselingCase, Referral

CASE_TRANSITIONS = {
    CounselingCase.Status.DRAFT: {CounselingCase.Status.ACTIVE, CounselingCase.Status.ARCHIVED},
    CounselingCase.Status.ACTIVE: {CounselingCase.Status.CLOSED},
    CounselingCase.Status.CLOSED: {CounselingCase.Status.ARCHIVED},
    CounselingCase.Status.ARCHIVED: set(),
}


def transition_case(*, case, target_status):
    with transaction.atomic():
        locked = CounselingCase.objects.select_for_update().get(pk=case.pk)
        if target_status not in CASE_TRANSITIONS[locked.status]:
            raise ValidationError(
                {"target_status": "This counseling case transition is not allowed."}
            )
        now = timezone.now()
        locked.status = target_status
        update_fields = ["status", "updated_at"]
        if target_status == CounselingCase.Status.ACTIVE:
            locked.opened_at = now
            update_fields.append("opened_at")
        if target_status in {CounselingCase.Status.CLOSED, CounselingCase.Status.ARCHIVED}:
            locked.closed_at = now
            update_fields.append("closed_at")
        locked.full_clean(exclude=["id"])
        locked.save(update_fields=update_fields)
        return locked


def accept_referral(*, referral, actor):
    """Create a target-school case without copying any confidential sessions."""
    with transaction.atomic():
        locked = (
            Referral.objects.select_for_update()
            .select_related("source_case", "target_enrollment__school")
            .get(pk=referral.pk)
        )
        if locked.status == Referral.Status.ACCEPTED:
            return locked
        if locked.status != Referral.Status.SENT:
            raise ValidationError({"status": "Only a sent referral may be accepted."})
        if locked.target_counselor_id != actor.id:
            raise ValidationError({"detail": "Only the target counselor may accept this referral."})
        target = locked.target_enrollment
        created_case = CounselingCase.objects.create(
            organization=target.school.organization,
            school=target.school,
            enrollment=target,
            assigned_counselor=actor,
            opened_by=actor,
            status=CounselingCase.Status.ACTIVE,
            opened_at=timezone.now(),
        )
        locked.status = Referral.Status.ACCEPTED
        locked.accepted_case = created_case
        locked.save(update_fields=["status", "accepted_case", "updated_at"])
        return locked
