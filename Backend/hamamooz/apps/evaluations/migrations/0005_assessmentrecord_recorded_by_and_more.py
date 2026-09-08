import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluations', '0004_dynamic_assessment_tables'),
        ('organizations', '0001_initial'),
        ('students', '0005_alter_student_photo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='assessmentrecord',
            name='recorded_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='dynamic_assessment_records', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='assessmentperiod',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='assessmentperiod',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='assessmentperiod',
            name='period_type',
            field=models.CharField(choices=[('monthly', 'Monthly'), ('season', 'Season'), ('exam', 'Exam'), ('custom', 'Custom')], default='custom', max_length=20),
        ),
        migrations.AlterField(
            model_name='assessmentrecord',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='assessmentrecord',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AddConstraint(
            model_name='assessmentperiod',
            constraint=models.UniqueConstraint(fields=('academic_year', 'title'), name='uq_assessment_period_title_year'),
        ),
        migrations.AddConstraint(
            model_name='assessmentrecord',
            constraint=models.UniqueConstraint(fields=('student', 'period', 'indicator'), name='uq_student_period_indicator_record'),
        ),
    ]
