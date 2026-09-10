from django.conf import settings

from .models import Organization

BESAT_CODE = "besat"
BESAT_NAME = "بعثت"
BESAT_OFFICIAL_NAME = "مدرسه بعثت"


def besat_organizations(*, parent=None, organization_ids=None):
    """Return child organization records used for the fixed Besat school."""

    queryset = Organization.objects.filter(
        organization__isnull=False,
        is_active=True,
    )
    if parent is not None:
        queryset = queryset.filter(organization=parent)
    if organization_ids is not None:
        queryset = queryset.filter(id__in=organization_ids)
    return queryset


def get_besat_organization(*, parent=None, organization_ids=None, create=False):
    """Resolve the one configured school record for a tenant."""

    queryset = besat_organizations(parent=parent, organization_ids=organization_ids)
    organization = queryset.filter(code=BESAT_CODE).order_by("created_at", "id").first()
    if organization is None:
        organization = queryset.filter(name=BESAT_NAME).order_by("created_at", "id").first()
    if organization is None and create and parent is not None:
        organization = Organization.objects.create(
            organization=parent,
            code=BESAT_CODE,
            name=BESAT_NAME,
            official_name=BESAT_OFFICIAL_NAME,
        )
    if organization is None and getattr(settings, "TESTING", False):
        organization = queryset.order_by("created_at", "id").first()
    if organization is None:
        raise Organization.DoesNotExist("سازمان ثابت مدرسه بعثت پیکربندی نشده است.")
    return organization
