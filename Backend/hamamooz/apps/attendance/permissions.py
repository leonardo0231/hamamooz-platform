from hamamooz.apps.accounts.access import user_has_role
from hamamooz.apps.accounts.models import Role

ATTENDANCE_WRITERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
    Role.OPERATOR,
    Role.TEACHER,
]

ATTENDANCE_REVIEWERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
]

ATTENDANCE_POLICY_MANAGERS = ATTENDANCE_REVIEWERS

BROAD_ATTENDANCE_ROLES = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
    Role.OPERATOR,
]


def can_manage_session(user, session):
    if user_has_role(
        user,
        BROAD_ATTENDANCE_ROLES,
        organization_id=session.organization_id,
        school_id=session.school_id,
    ):
        return True
    return bool(
        session.scope == session.Scope.PERIOD
        and session.course_offering_id
        and session.course_offering.teacher_id == user.id
        and user_has_role(
            user,
            [Role.TEACHER],
            organization_id=session.organization_id,
            school_id=session.school_id,
        )
    )
