from django.db.models import Q

from hamamooz.apps.accounts.access import selected_school_ids, user_has_role
from hamamooz.apps.accounts.models import Role

GUIDANCE_MANAGEMENT_ROLES = [
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
    Role.STUDENT_AFFAIRS_DEPUTY,
]
GUIDANCE_WRITE_ROLES = [*GUIDANCE_MANAGEMENT_ROLES, Role.GUIDE_TEACHER]


def is_guidance_manager(user, school_id):
    return user_has_role(user, GUIDANCE_MANAGEMENT_ROLES, school_id=school_id)


def guide_assignment_queryset(request):
    """Return only assignments the request principal may inspect.

    A guide teacher is deliberately limited to assignments that name them; broad
    staff roles retain school-scoped access.  This is used by every child
    resource rather than trusting an assignment id supplied by the client.
    """
    from .models import GuideTeacherAssignment

    school_ids = selected_school_ids(request)
    broad = Q()
    for school_id in school_ids:
        if is_guidance_manager(request.user, school_id):
            broad |= Q(enrollment__school_id=school_id)
    own = Q(guide_teacher=request.user, enrollment__school_id__in=school_ids)
    return GuideTeacherAssignment.objects.filter(broad | own)


def can_write_assignment_data(request, assignment):
    return (
        is_guidance_manager(request.user, assignment.school_id)
        or assignment.guide_teacher_id == request.user.id
    )
