from __future__ import annotations

from typing import Any, ClassVar

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        normalized = super().normalize_email(email or "")
        return normalized.strip().lower()

    def _create_user(
        self,
        email: str,
        password: str | None,
        **extra_fields: Any,
    ) -> User:
        normalized_email = self.normalize_email(email)

        if not normalized_email:
            raise ValueError("Email address is required.")

        user = self.model(
            email=normalized_email,
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        return self._create_user(
            email,
            password,
            **extra_fields,
        )

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(
                "Superuser must have is_staff=True."
            )

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "Superuser must have is_superuser=True."
            )

        return self._create_user(
            email,
            password,
            **extra_fields,
        )


class User(AbstractUser):
    username = None

    email = models.EmailField(
        "email address",
        unique=True,
    )

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects = UserManager()

    class Meta:
        ordering: ClassVar[list[str]] = ["email"]

        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["is_active", "email"],
                name="acct_user_active_email_idx",
            )
        ]

        constraints = (
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.email = type(self).objects.normalize_email(
            self.email
        )

    def save(self, *args, **kwargs) -> None:
        self.email = type(self).objects.normalize_email(
            self.email
        )

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.get_full_name() or self.email


class LoginAttempt(models.Model):
    identifier_hash = models.CharField(
        max_length=64,
        db_index=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="login_attempts",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    succeeded = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar[list[str]] = [
            "-created_at",
            "-id",
        ]

        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["identifier_hash", "created_at"],
                name="login_identifier_time_idx",
            ),
            models.Index(
                fields=["ip_address", "created_at"],
                name="login_ip_time_idx",
            ),
        ]

    def __str__(self) -> str:
        result = "success" if self.succeeded else "failure"
        return f"{self.identifier_hash}: {result}"