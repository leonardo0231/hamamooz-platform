from apps.permissions.models import SystemRole


def has_role(user, role):

    return user.school_memberships.filter(
        is_active=True,
        roles__role=role
    ).exists()



def can_manage_school(user, school):

    if user.is_superuser:
        return True


    return school.memberships.filter(
        user=user,
        is_active=True,
        roles__role__in=[
            SystemRole.SCHOOL_MANAGER,
            SystemRole.ORGANIZATION_MANAGER,
        ]
    ).exists()