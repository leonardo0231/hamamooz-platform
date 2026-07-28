from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("imports", "0003_alter_importjob_import_type")]

    operations = [
        migrations.AlterField(
            model_name="importjob",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "در صف"),
                    ("processing", "در حال پردازش"),
                    ("completed", "تکمیل‌شده"),
                    ("failed", "ناموفق"),
                    ("cancelled", "لغوشده"),
                ],
                db_index=True,
                default="queued",
                max_length=20,
            ),
        ),
    ]
