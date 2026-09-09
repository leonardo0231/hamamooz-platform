from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('imports', '0006_remove_importjob_uq_active_import_file_scope_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='importjob',
            name='status',
            field=models.CharField(choices=[('queued', 'در صف'), ('uploaded', 'آپلود شده'), ('analyzing', 'در حال تحلیل'), ('preview_ready', 'پیش\u200cنمایش آماده'), ('confirmed', 'تایید شده'), ('processing', 'در حال پردازش'), ('completed', 'تکمیل\u200cشده'), ('failed', 'ناموفق'), ('cancelled', 'لغوشده')], db_index=True, default='uploaded', max_length=20),
        ),
    ]
