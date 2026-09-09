import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0005_assessmentrecord_recorded_by_and_more"),
        ("imports", "0008_datapathimport_importjob_data_path_import_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessmentrecord",
            name="raw_value",
            field=models.CharField(blank=True, max_length=5000),
        ),
        migrations.AddField(
            model_name="assessmentrecord",
            name="status",
            field=models.CharField(default="recorded", max_length=20),
        ),
        migrations.AddField(
            model_name="assessmentrecord",
            name="value_kind",
            field=models.CharField(default="rubric_5", max_length=30),
        ),
        migrations.AddField(
            model_name="assessmentrecord",
            name="source_import_job",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="dynamic_assessment_records",
                to="imports.importjob",
            ),
        ),
    ]
