from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("imports", "0004_importjob_cancelled")]

    operations = [
        migrations.AddField(
            model_name="importjob",
            name="result_summary",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="importjob",
            name="import_type",
            field=models.CharField(
                choices=[
                    ("students", "دانش‌آموزان"),
                    ("enrollments", "ثبت‌نام و کلاس‌بندی"),
                    ("scores", "نمرات اولیه"),
                    ("monthly_evaluations", "ارزیابی جامع ماهانه"),
                    ("comprehensive_school", "فایل جامع مدرسه"),
                ],
                max_length=30,
            ),
        ),
    ]
