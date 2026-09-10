from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("imports", "0010_subject_exam_result"),
    ]
    operations = [
        migrations.AddField(
            model_name="datasourcemanifest",
            name="ingest_status",
            field=models.CharField(
                choices=[
                    ("not_processed", "ثبت رسمی نشده"),
                    ("completed", "ثبت شد"),
                    ("partial", "ثبت ناقص با حفظ داده خام"),
                    ("failed", "خطا در ثبت"),
                ],
                db_index=True,
                default="not_processed",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="datasourcemanifest",
            name="ingest_summary",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="datasourcemanifest",
            name="ingested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="datasourcemanifest",
            index=models.Index(
                fields=["school", "ingest_status"],
                name="imports_dat_school_ingest_idx",
            ),
        ),
    ]
