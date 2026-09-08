from django.db import migrations, models

PAGE_SIZE = "a3_landscape"


def normalize_report_print_profile(apps, schema_editor):
    ReportBatch = apps.get_model("reports", "ReportBatch")
    ReportTemplate = apps.get_model("reports", "ReportTemplate")

    # Preserve the records, but remove layout ambiguity from every persisted
    # report request before the fixed printable profile becomes the default.
    ReportBatch.objects.exclude(page_size=PAGE_SIZE).update(page_size=PAGE_SIZE)
    for template in ReportTemplate.objects.all().only("id", "presentation"):
        presentation = dict(template.presentation or {})
        if presentation.get("page_size") != PAGE_SIZE:
            presentation["page_size"] = PAGE_SIZE
            template.presentation = presentation
            template.save(update_fields=["presentation"])


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0006_rename_reports_rep_school__batch_status_idx_reports_batch_school_term_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reportbatch",
            name="page_size",
            field=models.CharField(default=PAGE_SIZE, max_length=20),
        ),
        migrations.RunPython(normalize_report_print_profile, migrations.RunPython.noop),
    ]
