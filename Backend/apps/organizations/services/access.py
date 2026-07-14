from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import (
    AccessAuditEvent,
    RoleAssignment,
    School,
    SchoolMembership,
)
from apps.organizations.policies import (
    can_grant_role,
    can_manage_membership,
    can_manage_school_memberships,
    can_revoke_role,
)
from apps.permissions.models import SystemRole


class AccessServiceError(Exception):
    pass


class AccessDeniedError(AccessServiceError):
    pass


class AccessValidationError(AccessServiceError):
    pass


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
        reason=reason.strip(),
    )


def _locked_membership(
    membership: SchoolMembership,
) -> SchoolMembership:
    return (
        SchoolMembership.objects
        .select_for_update()
        .select_related(
            "user",
            "school",
            "school__organization",
        )
        .get(pk=membership.pk)
    )


@transaction.atomic
def create_membership(
    *,
    user: User,
    school: School,
    actor: User,
    reason: str = "",
) -> SchoolMembership:
    locked_school = (
        School.objects
        .select_for_update()
        .select_related("organization")
        .get(pk=school.pk)
    )

    if not user.is_active:
        raise AccessValidationError(
            "An inactive user cannot receive a membership."
        )

    if not can_manage_school_memberships(
        actor,
        locked_school,
    ):
        raise AccessDeniedError(
            "You are not allowed to create "
            "memberships for this school."
        )

    existing = SchoolMembership.objects.filter(
        user=user,
        school=locked_school,
    ).first()

    if existing is not None:
        if existing.is_active:
            raise AccessValidationError(
                "An active membership already exists."
            )

        raise AccessValidationError(
            "An inactive membership already exists. "
            "Use the activate action."
        )

    membership = SchoolMembership.objects.create(
        user=user,
        school=locked_school,
        is_active=True,
    )

    _create_access_event(
        action=AccessAuditEvent.Action.MEMBERSHIP_CREATED,
        actor=actor,
        membership=membership,
        reason=reason,
    )

    return membership


@transaction.atomic
def activate_membership(
    *,
    membership: SchoolMembership,
    actor: User,
    reason: str = "",
) -> SchoolMembership:
    locked = _locked_membership(membership)

    if not can_manage_membership(actor, locked):
        raise AccessDeniedError(
            "You are not allowed to activate "
            "this membership."
        )

    if locked.is_active:
        return locked

    if not locked.user.is_active:
        raise AccessValidationError(
            "An inactive user cannot have "
            "an active membership."
        )

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
    reason = reason.strip()

    if not reason:
        raise AccessValidationError(
            "A deactivation reason is required."
        )

    locked = _locked_membership(membership)

    if not can_manage_membership(actor, locked):
        raise AccessDeniedError(
            "You are not allowed to deactivate "
            "this membership."
        )

    if not locked.is_active:
        return locked

    now = timezone.now()

    assignments = list(
        locked.roles
        .select_for_update()
        .filter(is_active=True)
    )

    for assignment in assignments:
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
        action=(
            AccessAuditEvent.Action
            .MEMBERSHIP_DEACTIVATED
        ),
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
        raise AccessValidationError(
            "Unknown school-scoped role."
        ) from exc

    locked_membership = _locked_membership(
        membership
    )

    if not locked_membership.is_active:
        raise AccessValidationError(
            "Roles cannot be granted to "
            "an inactive membership."
        )

    if not can_grant_role(
        actor,
        locked_membership,
        normalized_role.value,
    ):
        raise AccessDeniedError(
            "You are not allowed to grant this role."
        )

    assignment, created = (
        RoleAssignment.objects.get_or_create(
            membership=locked_membership,
            role=normalized_role.value,
            defaults={
                "is_active": True,
                "granted_by": actor,
                "granted_at": timezone.now(),
            },
        )
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
    reason = reason.strip()

    if not reason:
        raise AccessValidationError(
            "A revocation reason is required."
        )

    try:
        normalized_role = SystemRole(role)
    except ValueError as exc:
        raise AccessValidationError(
            "Unknown school-scoped role."
        ) from exc

    locked_membership = _locked_membership(
        membership
    )

    assignment = (
        RoleAssignment.objects
        .select_for_update()
        .filter(
            membership=locked_membership,
            role=normalized_role.value,
        )
        .first()
    )

    if assignment is None:
        raise AccessValidationError(
            "The requested role assignment does not exist."
        )

    if not can_revoke_role(actor, assignment):
        raise AccessDeniedError(
            "You are not allowed to revoke this role."
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