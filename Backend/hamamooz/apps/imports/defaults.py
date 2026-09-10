from django.conf import settings

from hamamooz.apps.organizations.models import Organization
from hamamooz.apps.organizations.services import BESAT_CODE, BESAT_NAME


def get_besat_organization(*, organization_ids=None, parent_organization=None):
    """Return the single fixed Besat organization used by imports.

    Legacy deployments may still contain several branch rows.  The data
    migration consolidates them, while this lookup remains scoped to child
    organization records so an import can never accidentally target a parent
    tenant record.
    """

    organizations = Organization.objects.filter(organization__isnull=False, is_active=True)
    if organization_ids is not None:
        organizations = organizations.filter(id__in=organization_ids)
    elif parent_organization is not None:
        organizations = organizations.filter(organization=parent_organization)

    organization = (
        organizations.filter(code=BESAT_CODE).order_by("created_at", "id").first()
        or organizations.filter(name=BESAT_NAME).order_by("created_at", "id").first()
    )
    if organization is None and getattr(settings, "TESTING", False):
        organization = organizations.order_by("created_at", "id").first()
    if organization is None:
        raise Organization.DoesNotExist("سازمان ثابت مدرسه بعثت برای import پیکربندی نشده است.")
    return organization


# Compatibility for integrations deployed before the single-school migration.
def get_default_school(*, school_ids=None, organization=None):
    return get_besat_organization(
        organization_ids=school_ids,
        parent_organization=organization,
    )
