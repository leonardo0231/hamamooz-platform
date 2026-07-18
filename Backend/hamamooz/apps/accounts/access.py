from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import models
from rest_framework.exceptions import PermissionDenied

from hamamooz.apps.organizations.models import Organization, School

from .models import Role, RoleAssignment


def is_system_admin(user):
    if not user or not user.is_authenticated:
        return False
    return (
        user.is_superuser
        or RoleAssignment.objects.filter(user=user, role=Role.SYSTEM_ADMIN, is_active=True).exists()
    )


def accessible_organization_ids(user):
    if not user or not user.is_authenticated:
        return []
    if is_system_admin(user):
        return list(Organization.objects.values_list("id", flat=True))
    return list(
        RoleAssignment.objects.filter(user=user, is_active=True, organization__isnull=False)
        .values_list("organization_id", flat=True)
        .distinct()
    )


def administered_organization_ids(user):
    if not user or not user.is_authenticated:
        return []
    if is_system_admin(user):
        return list(Organization.objects.values_list("id", flat=True))
    return list(
        RoleAssignment.objects.filter(
            user=user,
            role=Role.ORGANIZATION_ADMIN,
            is_active=True,
            organization__isnull=False,
        )
        .values_list("organization_id", flat=True)
        .distinct()
    )


def accessible_school_ids(user):
    if not user or not user.is_authenticated:
        return []
    if is_system_admin(user):
        return list(School.objects.values_list("id", flat=True))
    assignments = RoleAssignment.objects.filter(user=user, is_active=True)
    organization_admin_ids = assignments.filter(role=Role.ORGANIZATION_ADMIN).values_list(
        "organization_id", flat=True
    )
    direct_school_ids = assignments.filter(school__isnull=False).values_list("school_id", flat=True)
    return list(
        School.objects.filter(
            models.Q(id__in=direct_school_ids)
            | models.Q(organization_id__in=organization_admin_ids)
        )
        .values_list("id", flat=True)
        .distinct()
    )


def selected_school_ids(request):
    allowed = set(accessible_school_ids(request.user))
    selected = request.headers.get("X-School-ID")
    if not selected:
        return list(allowed)
    try:
        selected_id = UUID(selected)
    except (ValueError, TypeError, ValidationError) as exc:
        raise PermissionDenied("هدر X-School-ID معتبر نیست.") from exc
    if selected_id not in allowed:
        raise PermissionDenied("به شعبه انتخاب‌شده دسترسی ندارید.")
    return [selected_id]


def user_has_role(user, roles, *, organization_id=None, school_id=None):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or is_system_admin(user):
        return True
    query = RoleAssignment.objects.filter(user=user, role__in=roles, is_active=True)
    if school_id:
        school_organization_id = (
            School.objects.filter(id=school_id).values_list("organization_id", flat=True).first()
        )
        if school_organization_id is None:
            return False
        if organization_id and str(organization_id) != str(school_organization_id):
            return False
        organization_id = school_organization_id
        query = query.filter(
            models.Q(school_id=school_id)
            | models.Q(role=Role.ORGANIZATION_ADMIN, organization_id=organization_id)
        )
    elif organization_id:
        query = query.filter(organization_id=organization_id)
    return query.exists()


def can_manage_role_assignment(user, assignment):
    """Return whether ``user`` may manage the holder of this exact role scope."""
    if is_system_admin(user):
        return True
    if assignment.role == Role.SYSTEM_ADMIN:
        return False
    if assignment.role == Role.ORGANIZATION_ADMIN:
        return user_has_role(
            user,
            [Role.ORGANIZATION_ADMIN],
            organization_id=assignment.organization_id,
        )
    return user_has_role(
        user,
        [Role.ORGANIZATION_ADMIN, Role.SCHOOL_MANAGER],
        organization_id=assignment.organization_id,
        school_id=assignment.school_id,
    )


def allowed_class_ids(user, school_ids):
    from hamamooz.apps.academics.models import CourseOffering
    from hamamooz.apps.organizations.models import ClassSection

    if is_system_admin(user):
        return list(
            ClassSection.objects.filter(school_id__in=school_ids).values_list("id", flat=True)
        )
    broad_school_ids = broad_access_school_ids(user, school_ids)
    broad_classes = ClassSection.objects.filter(school_id__in=broad_school_ids).values_list(
        "id", flat=True
    )
    teacher_classes = CourseOffering.objects.filter(
        teacher=user, class_section__school_id__in=school_ids
    ).values_list("class_section_id", flat=True)
    return list(set(broad_classes) | set(teacher_classes))


def broad_access_school_ids(user, school_ids):
    if is_system_admin(user):
        return list(school_ids)
    broad_roles = [
        Role.ORGANIZATION_ADMIN,
        Role.SCHOOL_MANAGER,
        Role.EDUCATIONAL_DEPUTY,
        Role.OPERATOR,
    ]
    assignments = RoleAssignment.objects.filter(user=user, is_active=True, role__in=broad_roles)
    broad_school_ids = set(
        assignments.filter(school_id__in=school_ids).values_list("school_id", flat=True)
    )
    broad_org_ids = assignments.filter(role=Role.ORGANIZATION_ADMIN).values_list(
        "organization_id", flat=True
    )
    broad_school_ids.update(
        School.objects.filter(id__in=school_ids, organization_id__in=broad_org_ids).values_list(
            "id", flat=True
        )
    )
    return list(broad_school_ids)
