from django.db.models import Q

from hamamooz.apps.accounts.access import selected_school_ids
from hamamooz.apps.accounts.models import Role, RoleAssignment

COUNSELING_SHARED_ROLES = [
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
    Role.STUDENT_AFFAIRS_DEPUTY,
]


def has_counselor_role(user, school_id):
    """Deliberately do not treat system_admin/superuser as a counselor."""
    return RoleAssignment.objects.filter(
        user=user,
        role=Role.COUNSELOR,
        school_id=school_id,
        is_active=True,
        is_deleted=False,
    ).exists()


def has_shared_counseling_role(user, school_id):
    """Deliberately do not treat global administrators as confidential readers."""
    return RoleAssignment.objects.filter(
        user=user,
        role__in=COUNSELING_SHARED_ROLES,
        school_id=school_id,
        is_active=True,
        is_deleted=False,
    ).exists()


def guide_teacher_case_queryset(request):
    from hamamooz.apps.guidance.models import GuideTeacherAssignment

    school_ids = RoleAssignment.objects.filter(
        user=request.user,
        role=Role.GUIDE_TEACHER,
        is_active=True,
        is_deleted=False,
    ).values_list("school_id", flat=True)
    return GuideTeacherAssignment.objects.filter(
        guide_teacher=request.user,
        enrollment__school_id__in=set(selected_school_ids(request)) & set(school_ids),
        ends_at__isnull=True,
    ).values_list("enrollment_id", flat=True)


def shared_case_queryset(request):
    from .models import CounselingCase

    school_ids = selected_school_ids(request)
    broad = Q()
    for school_id in school_ids:
        if has_shared_counseling_role(request.user, school_id):
            broad |= Q(school_id=school_id)
    counselor_school_ids = [
        school_id for school_id in school_ids if has_counselor_role(request.user, school_id)
    ]
    counselor = Q(assigned_counselor=request.user, school_id__in=counselor_school_ids)
    guide = Q(enrollment_id__in=guide_teacher_case_queryset(request))
    # Roles are checked in the scoped filters. A staff member with no applicable
    # confidential relationship receives an empty queryset rather than a leak.
    return CounselingCase.objects.filter(broad | counselor | guide)


def can_read_private_case(user, case):
    return case.assigned_counselor_id == user.id and has_counselor_role(user, case.school_id)


def can_manage_shared_case(user, case):
    return has_shared_counseling_role(user, case.school_id) or can_read_private_case(user, case)
