# Generated manually for the analytical report batch feature.

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0004_reportarchive_output_format"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportBatch",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("scope", models.CharField(choices=[("class", "Class"), ("school", "School")], max_length=10)),
                ("page_size", models.CharField(default="a3_landscape", max_length=20)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("processing", "Processing"), ("completed", "Completed"), ("partial", "Partially completed"), ("failed", "Failed")], db_index=True, default="queued", max_length=20)),
                ("zip_file", models.FileField(blank=True, upload_to="reports/batches/%Y/%m/")),
                ("total_count", models.PositiveIntegerField(default=0)),
                ("completed_count", models.PositiveIntegerField(default=0)),
                ("failed_count", models.PositiveIntegerField(default=0)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="report_batches", to="organizations.academicyear")),
                ("class_section", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="report_batches", to="organizations.classsection")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="report_batches", to="organizations.organization")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requested_report_batches", to=settings.AUTH_USER_MODEL)),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="report_batches", to="organizations.school")),
                ("term", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="report_batches", to="organizations.term")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ReportBatchItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed")], db_index=True, default="queued", max_length=20)),
                ("error_message", models.TextField(blank=True)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="reports.reportbatch")),
                ("enrollment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="report_batch_items", to="students.enrollment")),
                ("report", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="batch_item", to="reports.reportarchive")),
            ],
            options={"ordering": ["enrollment__student__last_name", "enrollment__student__first_name"]},
        ),
        migrations.AddIndex(model_name="reportbatch", index=models.Index(fields=["school", "academic_year", "term", "status"], name="reports_rep_school__batch_status_idx")),
        migrations.AddConstraint(model_name="reportbatchitem", constraint=models.UniqueConstraint(fields=("batch", "enrollment"), name="uq_report_batch_enrollment")),
    ]
