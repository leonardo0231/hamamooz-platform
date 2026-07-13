import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Count
from django.db.models.functions import Lower


def normalize_existing_emails(
    apps,
    schema_editor,
):
    User = apps.get_model(
        "accounts",
        "User",
    )

    duplicates = list(
        User.objects
        .annotate(email_ci=Lower("email"))
        .values("email_ci")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )

    if duplicates:
        values = ", ".join(
            str(item["email_ci"])
            for item in duplicates
        )

        raise RuntimeError(
            "Case-insensitive duplicate emails exist: "
            f"{values}. Resolve them before migration."
        )

    for user in User.objects.all().iterator():
        normalized = user.email.strip().lower()

        if user.email != normalized:
            user.email = normalized

            user.save(
                update_fields=("email",)
            )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LoginAttempt",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "identifier_hash",
                    models.CharField(
                        db_index=True,
                        max_length=64,
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "succeeded",
                    models.BooleanField(
                        default=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=(
                            django.db.models.deletion.SET_NULL
                        ),
                        related_name="login_attempts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": [
                    "-created_at",
                    "-id",
                ],
                "indexes": [
                    models.Index(
                        fields=[
                            "identifier_hash",
                            "created_at",
                        ],
                        name="login_identifier_time_idx",
                    ),
                    models.Index(
                        fields=[
                            "ip_address",
                            "created_at",
                        ],
                        name="login_ip_time_idx",
                    ),
                ],
            },
        ),
        migrations.RunPython(
            normalize_existing_emails,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            ),
        ),
    ]