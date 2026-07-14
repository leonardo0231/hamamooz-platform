import pytest
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.mark.django_db(transaction=True)
def test_email_is_case_insensitive_unique() -> None:
    user = User.objects.create_user(
        email="User@Example.com",
        password="StrongPass-12345",
    )

    assert user.email == "user@example.com"

    with pytest.raises(IntegrityError):
        User.objects.create_user(
            email="USER@example.com",
            password="StrongPass-12345",
        )


@pytest.mark.django_db
def test_login_accepts_email_case_variation() -> None:
    User.objects.create_user(
        email="user@example.com",
        password="StrongPass-12345",
    )

    response = APIClient().post(
        reverse("login"),
        {
            "email": "USER@EXAMPLE.COM",
            "password": "StrongPass-12345",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    assert "access" in response.json()
    assert "refresh" in response.json()


@pytest.mark.django_db
def test_password_change_revokes_old_access_and_refresh_tokens() -> None:
    User.objects.create_user(
        email="user@example.com",
        password="OldStrongPass-12345",
    )

    client = APIClient()

    login_response = client.post(
        reverse("login"),
        {
            "email": "user@example.com",
            "password": "OldStrongPass-12345",
        },
        format="json",
    )

    assert login_response.status_code == status.HTTP_200_OK

    access_token = login_response.json()["access"]
    refresh_token = login_response.json()["refresh"]

    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )

    change_response = client.post(
        reverse("change-password"),
        {
            "old_password": "OldStrongPass-12345",
            "new_password": "NewStrongPass-12345",
        },
        format="json",
    )

    assert (
        change_response.status_code
        == status.HTTP_204_NO_CONTENT
    )

    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )

    me_response = client.get(
        reverse("me")
    )

    assert (
        me_response.status_code
        == status.HTTP_401_UNAUTHORIZED
    )

    client.credentials()

    refresh_response = client.post(
        reverse("token-refresh"),
        {
            "refresh": refresh_token,
        },
        format="json",
    )

    assert (
        refresh_response.status_code
        == status.HTTP_401_UNAUTHORIZED
    )