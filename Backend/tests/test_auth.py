import pytest

from hamamooz.apps.core.models import AuditEvent


@pytest.mark.django_db
def test_jwt_login_returns_user_and_writes_audit(api_client, base_data):
    response = api_client.post(
        "/api/v1/auth/token/",
        {"username": "teacher1", "password": "Strong-pass-123"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["access"]
    assert response.data["refresh"]
    assert response.data["user"]["username"] == "teacher1"
    assert AuditEvent.objects.filter(action="auth.login", actor=base_data["teacher1"]).exists()


@pytest.mark.django_db
def test_jwt_login_accepts_email(api_client, base_data):
    response = api_client.post(
        "/api/v1/auth/token/",
        {"username": "teacher1@example.com", "password": "Strong-pass-123"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["user"]["username"] == "teacher1"


@pytest.mark.django_db
def test_auth_me_exposes_readable_role_scope_names(api_client, base_data):
    api_client.force_authenticate(user=base_data["teacher1"])

    response = api_client.get("/api/v1/auth/me/")

    assert response.status_code == 200
    assignment = response.data["role_assignments"][0]
    assert assignment["organization_name"] == base_data["organization"].name
    assert assignment["school_name"] == base_data["school1"].name
