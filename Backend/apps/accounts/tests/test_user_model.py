import pytest
from django.db import IntegrityError

from apps.accounts.models import User


@pytest.mark.django_db
def test_create_user_uses_normalized_unique_email() -> None:
    user = User.objects.create_user(email="Admin@EXAMPLE.COM", password="strong-test-password")

    assert user.email == "Admin@example.com"
    assert user.check_password("strong-test-password")
    assert not user.is_staff


@pytest.mark.django_db
def test_user_email_is_unique() -> None:
    User.objects.create_user(email="admin@example.com", password="strong-test-password")

    with pytest.raises(IntegrityError):
        User.objects.create_user(email="admin@example.com", password="another-password")
