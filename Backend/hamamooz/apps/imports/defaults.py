from hamamooz.apps.organizations.models import School

DEFAULT_SCHOOL_NAME = "بعثت"


def get_default_school(*, school_ids=None, organization=None):
    """Return the preferred active school for an import without a school.

    The demo seed uses branch codes rather than the historical ``بعثت`` name,
    so a missing named default must not turn into a server error when another
    active school is available.  Callers can scope the lookup to the schools a
    user may access; this keeps the fallback deterministic without widening
    import permissions.
    """

    schools = School.objects.filter(is_active=True)
    if school_ids is not None:
        schools = schools.filter(id__in=school_ids)
    elif organization is not None:
        schools = schools.filter(organization=organization)

    school = schools.filter(name=DEFAULT_SCHOOL_NAME).order_by("id").first()
    if school is None:
        school = schools.order_by("id").first()
    if school is None:
        raise School.DoesNotExist("No active school is configured for import defaults.")
    return school
