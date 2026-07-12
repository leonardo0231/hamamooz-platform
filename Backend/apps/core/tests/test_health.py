import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_health_endpoint_is_public() -> None:
    response = APIClient().get(reverse("health"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok", "service": "hamamooz-backend"}
    assert response.headers["X-Request-ID"]


@pytest.mark.django_db
def test_readiness_checks_database_and_cache() -> None:
    response = APIClient().get(reverse("readiness"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "cache": "ok"},
    }


def test_openapi_schema_is_generated() -> None:
    response = APIClient().get(reverse("schema"))

    assert response.status_code == status.HTTP_200_OK
    assert b"openapi" in response.content
