from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("attendance", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="parentnotification",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "در صف"),
                    ("processing", "در حال ارسال"),
                    ("sent", "ارسال‌شده"),
                    ("failed", "ناموفق"),
                    ("dead_letter", "متوقف‌شده"),
                    ("skipped", "ردشده"),
                ],
                db_index=True,
                default="queued",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="parentnotification",
            name="next_attempt_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
