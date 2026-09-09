from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('imports', '0005_importjob_comprehensive_school'),
        ('organizations', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='importjob',
            name='uq_active_import_file_scope',
        ),
        migrations.AddField(
            model_name='importjob',
            name='preview_summary',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='importjob',
            name='status',
            field=models.CharField(choices=[('uploaded', 'آپلود شده'), ('analyzing', 'در حال تحلیل'), ('preview_ready', 'پیش\u200cنمایش آماده'), ('confirmed', 'تایید شده'), ('processing', 'در حال پردازش'), ('completed', 'تکمیل\u200cشده'), ('failed', 'ناموفق'), ('cancelled', 'لغوشده')], db_index=True, default='uploaded', max_length=20),
        ),
        migrations.AddConstraint(
            model_name='importjob',
            constraint=models.UniqueConstraint(condition=models.Q(('is_deleted', False), ('status__in', ['uploaded', 'analyzing', 'preview_ready', 'confirmed', 'processing', 'completed'])), fields=('organization', 'school', 'import_type', 'checksum'), name='uq_active_import_file_scope'),
        ),
    ]
