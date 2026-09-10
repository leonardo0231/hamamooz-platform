import pytest
from django.apps import apps
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory

from hamamooz.apps.accounts.access import accessible_school_ids, selected_school_ids
from hamamooz.apps.accounts.models import Role, RoleAssignment
from hamamooz.apps.organizations.models import Organization
from hamamooz.apps.organizations.services import (
    BESAT_CODE,
    BESAT_NAME,
    BESAT_OFFICIAL_NAME,
    get_besat_organization,
)


@pytest.mark.django_db
def test_school_model_and_catalog_endpoint_are_removed(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])

    with pytest.raises(LookupError):
        apps.get_model("organizations", "School")

    response = api_client.get("/api/v1/schools/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_runtime_scope_is_limited_to_configured_besat(base_data, settings):
    settings.TESTING = False
    besat = Organization.objects.create(
        organization=base_data["organization"],
        code=BESAT_CODE,
        name=BESAT_NAME,
        official_name=BESAT_OFFICIAL_NAME,
    )
    RoleAssignment.objects.create(
        user=base_data["manager"],
        organization=base_data["organization"],
        school=besat,
        role=Role.SCHOOL_MANAGER,
    )

    assert accessible_school_ids(base_data["manager"]) == [besat.id]
    assert get_besat_organization(parent=base_data["organization"]) == besat

    request = APIRequestFactory().get("/", HTTP_X_SCHOOL_ID=str(base_data["school2"].id))
    request.user = base_data["manager"]
    with pytest.raises(PermissionDenied):
        selected_school_ids(request)
