from hamamooz.apps.schools.models import School


DEFAULT_SCHOOL_NAME = "بعثت"


def get_default_school():

    return School.objects.get(
        name=DEFAULT_SCHOOL_NAME
    )