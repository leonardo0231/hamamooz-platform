"""Audience-aware visibility rules for human-reviewed recommendations.

Recommendations are not a generic staff feed.  An audience-specific record is
the unit of authorization: a counselor recommendation may be private even
when a different audience receives a sibling recommendation from the same
signal.  These rules intentionally keep counselor-targeted records out of the
normal system-admin and manager path.
"""

from django.db.models import Q
from django.utils import timezone

from hamamooz.apps.accounts.access import is_system_admin, selected_school_ids
from hamamooz.apps.accounts.models import Role, RoleAssignment
from hamamooz.apps.organizations.models import School

from .models import Recommendation

RECOMMENDATION_REVIEWERS = [
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
    Role.STUDENT_AFFAIRS_DEPUTY,
]

RECOMMENDATION_TRANSITION_CANDIDATES = [
    *RECOMMENDATION_REVIEWERS,
    Role.COUNSELOR,
    Role.GUIDE_TEACHER,
    Role.TEACHER,
]


def _direct_broad_school_ids(user, school_ids):
    """Return school scope of non-confidential staff reviewers only."""

    assignments = RoleAssignment.objects.filter(
        user=user,
        is_active=True,
        is_deleted=False,
    )
    direct_school_ids = assignments.filter(
        role__in=[Role.SCHOOL_MANAGER, Role.EDUCATIONAL_DEPUTY, Role.STUDENT_AFFAIRS_DEPUTY],
        school_id__in=school_ids,
    ).values_list("school_id", flat=True)
    organization_ids = assignments.filter(
        role=Role.ORGANIZATION_ADMIN,
        organization_id__isnull=False,
    ).values_list("organization_id", flat=True)
    organization_school_ids = School.objects.filter(
        id__in=school_ids,
        organization_id__in=organization_ids,
    ).values_list("id", flat=True)
    return set(direct_school_ids) | set(organization_school_ids)


def _teacher_enrollment_ids(user, school_ids):
    from hamamooz.apps.academics.models import CourseOffering

    class_ids = CourseOffering.objects.filter(
        teacher=user,
        class_section__school_id__in=school_ids,
        is_active=True,
    ).values_list("class_section_id", flat=True)
    from hamamooz.apps.students.models import Enrollment

    return Enrollment.objects.filter(
        school_id__in=school_ids,
        class_section_id__in=class_ids,
    ).values_list("id", flat=True)


def _guide_enrollment_ids(user, school_ids):
    from hamamooz.apps.guidance.models import GuideTeacherAssignment

    today = timezone.localdate()
    return (
        GuideTeacherAssignment.objects.filter(
            guide_teacher=user,
            enrollment__school_id__in=school_ids,
            starts_at__lte=today,
        )
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gte=today))
        .values_list("enrollment_id", flat=True)
    )


def _counselor_enrollment_ids(user, school_ids):
    from hamamooz.apps.counseling.models import CounselingCase

    return CounselingCase.objects.filter(
        assigned_counselor=user,
        school_id__in=school_ids,
        is_deleted=False,
    ).values_list("enrollment_id", flat=True)


def visible_recommendations_queryset(request):
    """Return only audience records visible to the authenticated principal."""

    school_ids = selected_school_ids(request)
    if not school_ids:
        return Recommendation.objects.none()

    # System administration is intentionally *not* a bypass for counselor
    # audience records.  It can operate the non-confidential product domains.
    if is_system_admin(request.user):
        return Recommendation.objects.filter(school_id__in=school_ids).exclude(
            audience=Recommendation.Audience.COUNSELOR
        )

    visibility = Q()
    has_visibility = False
    broad_school_ids = _direct_broad_school_ids(request.user, school_ids)
    if broad_school_ids:
        visibility |= Q(school_id__in=broad_school_ids) & ~Q(
            audience=Recommendation.Audience.COUNSELOR
        )
        has_visibility = True

    teacher_enrollment_ids = _teacher_enrollment_ids(request.user, school_ids)
    if teacher_enrollment_ids:
        visibility |= Q(
            school_id__in=school_ids,
            enrollment_id__in=teacher_enrollment_ids,
            audience=Recommendation.Audience.TEACHER,
        )
        has_visibility = True

    guide_enrollment_ids = _guide_enrollment_ids(request.user, school_ids)
    if guide_enrollment_ids:
        visibility |= Q(
            school_id__in=school_ids,
            enrollment_id__in=guide_enrollment_ids,
            audience=Recommendation.Audience.GUIDE_TEACHER,
        )
        has_visibility = True

    counselor_enrollment_ids = _counselor_enrollment_ids(request.user, school_ids)
    if counselor_enrollment_ids:
        visibility |= Q(
            school_id__in=school_ids,
            enrollment_id__in=counselor_enrollment_ids,
            audience=Recommendation.Audience.COUNSELOR,
        )
        has_visibility = True

    return (
        Recommendation.objects.filter(visibility)
        if has_visibility
        else Recommendation.objects.none()
    )


def can_transition_recommendation(user, recommendation):
    """Verify that a reviewer may change this exact audience record."""

    class RequestLike:
        # Reuse the one visibility policy without trusting a client supplied id.
        def __init__(self):
            self.user = user
            self.headers = {"X-School-ID": str(recommendation.school_id)}

    if not visible_recommendations_queryset(RequestLike()).filter(pk=recommendation.pk).exists():
        return False
    if recommendation.audience == Recommendation.Audience.COUNSELOR:
        return recommendation.enrollment_id in set(
            _counselor_enrollment_ids(user, [recommendation.school_id])
        )
    if recommendation.audience == Recommendation.Audience.GUIDE_TEACHER:
        return recommendation.enrollment_id in set(
            _guide_enrollment_ids(user, [recommendation.school_id])
        ) or bool(_direct_broad_school_ids(user, [recommendation.school_id]))
    if recommendation.audience == Recommendation.Audience.TEACHER:
        return _teacher_enrollment_ids(user, [recommendation.school_id]).filter(
            pk=recommendation.enrollment_id
        ).exists() or bool(_direct_broad_school_ids(user, [recommendation.school_id]))
    return is_system_admin(user) or bool(_direct_broad_school_ids(user, [recommendation.school_id]))
