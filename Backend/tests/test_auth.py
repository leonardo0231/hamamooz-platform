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
