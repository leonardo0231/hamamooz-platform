from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import (
    AccessAuditEvent,
    RoleAssignment,
    SchoolMembership,
)
from apps.permissions.models import SystemRole
from apps.permissions.policies import (
    can_grant_role,
    can_manage_membership,
)


def _create_access_event(
    *,
    action: str,
    actor: User,
    membership: SchoolMembership,
    role: str = "",
    reason: str = "",
) -> AccessAuditEvent:
    return AccessAuditEvent.objects.create(
        actor=actor,
        target_user=membership.user,
        organization=membership.school.organization,
        school=membership.school,
        membership=membership,
        action=action,
        role=role,
        reason=reason,
    )


@transaction.atomic
def activate_membership(
    *,
    membership: SchoolMembership,
    actor: User,
    reason: str = "",
) -> SchoolMembership:
    locked = (
        SchoolMembership.objects
        .select_for_update()
        .select_related(
            "user",
            "school",
            "school__organization",
        )
        .get(pk=membership.pk)
    )

    if not can_manage_membership(actor, locked):
        raise PermissionDenied(
            "You are not allowed to activate this membership."
        )

    if locked.is_active:
        return locked

    locked.is_active = True
    locked.deactivated_at = None
    locked.deactivated_by = None
    locked.deactivation_reason = ""

    locked.save(
        update_fields=(
            "is_active",
            "deactivated_at",
            "deactivated_by",
            "deactivation_reason",
            "updated_at",
        )
    )

    _create_access_event(
        action=AccessAuditEvent.Action.MEMBERSHIP_ACTIVATED,
        actor=actor,
        membership=locked,
        reason=reason,
    )

    return locked


@transaction.atomic
def deactivate_membership(
    *,
    membership: SchoolMembership,
    actor: User,
    reason: str,
) -> SchoolMembership:
    if not reason.strip():
        raise ValidationError(
            "A deactivation reason is required."
        )

    locked = (
        SchoolMembership.objects
        .select_for_update()
        .select_related(
            "user",
            "school",
            "school__organization",
        )
        .get(pk=membership.pk)
    )

    if not can_manage_membership(actor, locked):
        raise PermissionDenied(
            "You are not allowed to deactivate this membership."
        )

    if not locked.is_active:
        return locked

    now = timezone.now()

    active_roles = list(
        locked.roles.select_for_update().filter(
            is_active=True,
        )
    )

    for assignment in active_roles:
        assignment.is_active = False
        assignment.revoked_at = now
        assignment.revoked_by = actor
        assignment.revocation_reason = (
            f"Membership deactivated: {reason}"
        )

        assignment.save(
            update_fields=(
                "is_active",
                "revoked_at",
                "revoked_by",
                "revocation_reason",
                "updated_at",
            )
        )

        _create_access_event(
            action=AccessAuditEvent.Action.ROLE_REVOKED,
            actor=actor,
            membership=locked,
            role=assignment.role,
            reason=assignment.revocation_reason,
        )

    locked.is_active = False
    locked.deactivated_at = now
    locked.deactivated_by = actor
    locked.deactivation_reason = reason

    locked.save(
        update_fields=(
            "is_active",
            "deactivated_at",
            "deactivated_by",
            "deactivation_reason",
            "updated_at",
        )
    )

    _create_access_event(
        action=AccessAuditEvent.Action.MEMBERSHIP_DEACTIVATED,
        actor=actor,
        membership=locked,
        reason=reason,
    )

    return locked


@transaction.atomic
def grant_role(
    *,
    membership: SchoolMembership,
    role: str,
    actor: User,
    reason: str = "",
) -> RoleAssignment:
    try:
        normalized_role = SystemRole(role)
    except ValueError as exc:
        raise ValidationError("Unknown school-scoped role.") from exc

    locked_membership = (
        SchoolMembership.objects
        .select_for_update()
        .select_related(
            "user",
            "school",
            "school__organization",
        )
        .get(pk=membership.pk)
    )

    if not locked_membership.is_active:
        raise ValidationError(
            "Roles cannot be granted to an inactive membership."
        )

    if not can_grant_role(
        actor,
        locked_membership,
        normalized_role.value,
    ):
        raise PermissionDenied(
            "You are not allowed to grant this role."
        )

    assignment, created = RoleAssignment.objects.get_or_create(
        membership=locked_membership,
        role=normalized_role.value,
        defaults={
            "is_active": True,
            "granted_by": actor,
            "granted_at": timezone.now(),
        },
    )

    if not created and assignment.is_active:
        return assignment

    if not created:
        assignment.is_active = True
        assignment.granted_at = timezone.now()
        assignment.granted_by = actor
        assignment.revoked_at = None
        assignment.revoked_by = None
        assignment.revocation_reason = ""

        assignment.save(
            update_fields=(
                "is_active",
                "granted_at",
                "granted_by",
                "revoked_at",
                "revoked_by",
                "revocation_reason",
                "updated_at",
            )
        )

    _create_access_event(
        action=AccessAuditEvent.Action.ROLE_GRANTED,
        actor=actor,
        membership=locked_membership,
        role=normalized_role.value,
        reason=reason,
    )

    return assignment


@transaction.atomic
def revoke_role(
    *,
    membership: SchoolMembership,
    role: str,
    actor: User,
    reason: str,
) -> RoleAssignment:
    if not reason.strip():
        raise ValidationError(
            "A revocation reason is required."
        )

    try:
        normalized_role = SystemRole(role)
    except ValueError as exc:
        raise ValidationError("Unknown school-scoped role.") from exc

    locked_membership = (
        SchoolMembership.objects
        .select_for_update()
        .select_related(
            "user",
            "school",
            "school__organization",
        )
        .get(pk=membership.pk)
    )

    if not can_grant_role(
        actor,
        locked_membership,
        normalized_role.value,
    ):
        raise PermissionDenied(
            "You are not allowed to revoke this role."
        )

    assignment = (
        RoleAssignment.objects
        .select_for_update()
        .get(
            membership=locked_membership,
            role=normalized_role.value,
        )
    )

    if not assignment.is_active:
        return assignment

    assignment.is_active = False
    assignment.revoked_at = timezone.now()
    assignment.revoked_by = actor
    assignment.revocation_reason = reason

    assignment.save(
        update_fields=(
            "is_active",
            "revoked_at",
            "revoked_by",
            "revocation_reason",
            "updated_at",
        )
    )

    _create_access_event(
        action=AccessAuditEvent.Action.ROLE_REVOKED,
        actor=actor,
        membership=locked_membership,
        role=normalized_role.value,
        reason=reason,
    )

    return assignment