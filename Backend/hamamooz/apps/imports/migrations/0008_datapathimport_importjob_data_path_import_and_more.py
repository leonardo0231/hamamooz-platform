import uuid

import django.db.models.deletion
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("imports", "0007_alter_importjob_status"),
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DataPathImport",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "source_root",
                    models.CharField(max_length=1000),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "در صف"),
                            ("scanning", "در حال اسکن مسیر Data"),
                            ("processing", "در حال ثبت اطلاعات"),
                            ("completed", "تکمیل‌شده"),
                            ("partial", "تکمیل با هشدار"),
                            ("failed", "ناموفق"),
                        ],
                        db_index=True,
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("overwrite_photos", models.BooleanField(default=False)),
                ("generate_reports", models.BooleanField(default=True)),
                (
                    "report_month",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[MinValueValidator(1), MaxValueValidator(12)],
                    ),
                ),
                ("manifest", models.JSONField(blank=True, default=dict)),
                ("result_summary", models.JSONField(blank=True, default=dict)),
                ("errors", models.JSONField(blank=True, default=list)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="data_path_imports",
                        to="organizations.organization",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="data_path_imports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "school",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="data_path_imports",
                        to="organizations.school",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="importjob",
            name="source_kind",
            field=models.CharField(
                choices=[
                    ("upload", "آپلود کاربر"),
                    ("data_path", "مسیر Data مخزن"),
                ],
                db_index=True,
                default="upload",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="importjob",
            name="data_path_import",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="file_jobs",
                to="imports.datapathimport",
            ),
        ),
        migrations.AddIndex(
            model_name="datapathimport",
            index=models.Index(fields=["school", "status"], name="imp_dp_school_status_idx"),
        ),
        migrations.AddIndex(
            model_name="datapathimport",
            index=models.Index(
                fields=["organization", "created_at"],
                name="imp_dp_org_created_idx",
            ),
        ),
    ]
