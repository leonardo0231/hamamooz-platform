import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.mark.django_db
def test_login_refresh_me_and_logout_flow() -> None:
    User.objects.create_user(email="user@example.com", password="StrongPass-12345")
    client = APIClient()

    login = client.post(
        reverse("auth-login"),
        {"email": "user@example.com", "password": "StrongPass-12345"},
        format="json",
    )
    assert login.status_code == status.HTTP_200_OK
    access = login.json()["access"]
    refresh = login.json()["refresh"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    me = client.get(reverse("auth-me"))
    assert me.status_code == status.HTTP_200_OK
    assert me.json()["email"] == "user@example.com"

    logout = client.post(reverse("auth-logout"), {"refresh": refresh}, format="json")
    assert logout.status_code == status.HTTP_204_NO_CONTENT

    refresh_response = client.post(reverse("auth-refresh"), {"refresh": refresh}, format="json")
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert refresh_response.json()["code"] == "authentication_required"


@pytest.mark.django_db
def test_me_requires_authentication_and_returns_standard_error() -> None:
    response = APIClient().get(reverse("auth-me"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    payload = response.json()
    assert payload["code"] == "authentication_required"
    assert payload["trace_id"]
