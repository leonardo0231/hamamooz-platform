import django.db.models.deletion
import hamamooz.apps.attendance.validators
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('academics', '0002_initial'),
        ('organizations', '0001_initial'),
        ('students', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AttendancePolicy',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('warning_absence_count', models.PositiveSmallIntegerField(default=3)),
                ('critical_absence_count', models.PositiveSmallIntegerField(default=5)),
                ('warning_absence_percent', models.DecimalField(decimal_places=2, default=Decimal('10.00'), max_digits=5)),
                ('critical_absence_percent', models.DecimalField(decimal_places=2, default=Decimal('20.00'), max_digits=5)),
                ('lookback_days', models.PositiveSmallIntegerField(default=30)),
                ('include_excused_absences', models.BooleanField(default=True)),
                ('require_evidence_for_excuse', models.BooleanField(default=False)),
                ('notify_guardians', models.BooleanField(default=True)),
                ('notification_channels', models.JSONField(blank=True, default=list)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('academic_year', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attendance_policies', to='organizations.academicyear')),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attendance_policies', to='organizations.school')),
            ],
            options={
                'ordering': ['school', '-academic_year__starts_on'],
            },
        ),
        migrations.CreateModel(
            name='AttendanceAlert',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('scope', models.CharField(choices=[('daily', 'روزانه'), ('period', 'زنگ/کلاس')], max_length=20)),
                ('severity', models.CharField(choices=[('warning', 'هشدار'), ('critical', 'بحرانی')], db_index=True, max_length=20)),
                ('period_start', models.DateField()),
                ('period_end', models.DateField()),
                ('absence_count', models.PositiveIntegerField()),
                ('total_sessions', models.PositiveIntegerField()),
                ('absence_percent', models.DecimalField(decimal_places=2, max_digits=5)),
                ('status', models.CharField(choices=[('open', 'باز'), ('acknowledged', 'مشاهده\u200cشده'), ('resolved', 'رفع\u200cشده')], db_index=True, default='open', max_length=20)),
                ('acknowledged_at', models.DateTimeField(blank=True, null=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('academic_year', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attendance_alerts', to='organizations.academicyear')),
                ('acknowledged_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='acknowledged_attendance_alerts', to=settings.AUTH_USER_MODEL)),
                ('enrollment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attendance_alerts', to='students.enrollment')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='resolved_attendance_alerts', to=settings.AUTH_USER_MODEL)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attendance_alerts', to='organizations.school')),
                ('policy', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='alerts', to='attendance.attendancepolicy')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AttendanceRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('present', 'حاضر'), ('absent_excused', 'غیبت موجه'), ('absent_unexcused', 'غیبت غیرموجه')], db_index=True, default='present', max_length=30)),
                ('arrival_time', models.TimeField(blank=True, null=True)),
                ('departure_time', models.TimeField(blank=True, null=True)),
                ('late_minutes', models.PositiveSmallIntegerField(default=0)),
                ('early_leave_minutes', models.PositiveSmallIntegerField(default=0)),
                ('note', models.CharField(blank=True, max_length=500)),
                ('absence_reason', models.TextField(blank=True)),
                ('excuse_status', models.CharField(choices=[('not_required', 'نیاز ندارد'), ('pending', 'در انتظار تأیید'), ('approved', 'تأییدشده'), ('rejected', 'ردشده')], db_index=True, default='not_required', max_length=20)),
                ('excuse_submitted_at', models.DateTimeField(blank=True, null=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('review_note', models.TextField(blank=True)),
                ('revision', models.PositiveIntegerField(default=1)),
                ('enrollment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attendance_records', to='students.enrollment')),
                ('excuse_submitted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='submitted_attendance_excuses', to=settings.AUTH_USER_MODEL)),
                ('recorded_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attendance_records', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='reviewed_attendance_excuses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['session', 'enrollment__student__last_name', 'enrollment__student__first_name'],
            },
        ),
        migrations.CreateModel(
            name='AbsenceEvidence',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('file', models.FileField(max_length=500, upload_to=hamamooz.apps.attendance.validators.attendance_evidence_upload_to, validators=[hamamooz.apps.attendance.validators.validate_attendance_evidence])),
                ('original_name', models.CharField(max_length=255)),
                ('content_type', models.CharField(blank=True, max_length=100)),
                ('size_bytes', models.PositiveIntegerField()),
                ('description', models.CharField(blank=True, max_length=300)),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='uploaded_absence_evidence', to=settings.AUTH_USER_MODEL)),
                ('attendance_record', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='evidence_files', to='attendance.attendancerecord')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AttendanceRecordRevision',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reason', models.TextField()),
                ('before', models.JSONField(default=dict)),
                ('after', models.JSONField(default=dict)),
                ('attendance_record', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='history', to='attendance.attendancerecord')),
                ('changed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attendance_revisions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AttendanceSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('session_date', models.DateField(db_index=True)),
                ('scope', models.CharField(choices=[('daily', 'روزانه'), ('period', 'زنگ/کلاس')], db_index=True, max_length=20)),
                ('period_number', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('title', models.CharField(blank=True, max_length=150)),
                ('starts_at', models.TimeField(blank=True, null=True)),
                ('ends_at', models.TimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('draft', 'پیش\u200cنویس'), ('finalized', 'نهایی\u200cشده'), ('cancelled', 'لغوشده')], db_index=True, default='draft', max_length=20)),
                ('finalized_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('academic_year', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attendance_sessions', to='organizations.academicyear')),
                ('class_section', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attendance_sessions', to='organizations.classsection')),
                ('course_offering', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attendance_sessions', to='academics.courseoffering')),
                ('finalized_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='finalized_attendance_sessions', to=settings.AUTH_USER_MODEL)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attendance_sessions', to='organizations.school')),
                ('taken_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='taken_attendance_sessions', to=settings.AUTH_USER_MODEL)),
                ('term', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attendance_sessions', to='organizations.term')),
            ],
            options={
                'ordering': ['-session_date', 'class_section', 'period_number'],
            },
        ),
        migrations.AddField(
            model_name='attendancerecord',
            name='session',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='records', to='attendance.attendancesession'),
        ),
        migrations.CreateModel(
            name='ParentNotification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('kind', models.CharField(choices=[('absence', 'گزارش غیبت'), ('summary', 'گزارش دوره\u200cای'), ('alert', 'هشدار غیبت بیش از حد')], max_length=20)),
                ('channel', models.CharField(choices=[('in_app', 'داخل سامانه'), ('email', 'ایمیل'), ('sms', 'پیامک')], db_index=True, max_length=20)),
                ('recipient', models.CharField(blank=True, max_length=255)),
                ('subject', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('status', models.CharField(choices=[('queued', 'در صف'), ('sent', 'ارسال\u200cشده'), ('failed', 'ناموفق'), ('skipped', 'ردشده')], db_index=True, default='queued', max_length=20)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True)),
                ('dedupe_key', models.CharField(max_length=160, unique=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('alert', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='parent_notifications', to='attendance.attendancealert')),
                ('attendance_record', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='parent_notifications', to='attendance.attendancerecord')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_parent_notifications', to=settings.AUTH_USER_MODEL)),
                ('enrollment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='parent_notifications', to='students.enrollment')),
                ('guardian', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attendance_notifications', to='students.guardian')),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='parent_notifications', to='organizations.school')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attendance_notifications', to='students.student')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='attendancepolicy',
            constraint=models.UniqueConstraint(condition=models.Q(('is_deleted', False)), fields=('school', 'academic_year'), name='uq_attendance_policy_school_year'),
        ),
        migrations.AddIndex(
            model_name='attendancealert',
            index=models.Index(fields=['school', 'academic_year', 'status', 'severity'], name='attendance__school__185292_idx'),
        ),
        migrations.AddIndex(
            model_name='attendancealert',
            index=models.Index(fields=['enrollment', 'scope', 'status'], name='attendance__enrollm_766d1b_idx'),
        ),
        migrations.AddConstraint(
            model_name='attendancealert',
            constraint=models.UniqueConstraint(condition=models.Q(('is_deleted', False), ('status__in', ['open', 'acknowledged'])), fields=('policy', 'enrollment', 'scope', 'severity'), name='uq_active_attendance_alert'),
        ),
        migrations.AddIndex(
            model_name='absenceevidence',
            index=models.Index(fields=['attendance_record', 'created_at'], name='attendance__attenda_569c09_idx'),
        ),
        migrations.AddIndex(
            model_name='attendancesession',
            index=models.Index(fields=['school', 'academic_year', 'session_date', 'scope'], name='attendance__school__66c9ea_idx'),
        ),
        migrations.AddIndex(
            model_name='attendancesession',
            index=models.Index(fields=['class_section', 'session_date', 'status'], name='attendance__class_s_43ef8c_idx'),
        ),
        migrations.AddConstraint(
            model_name='attendancesession',
            constraint=models.UniqueConstraint(condition=models.Q(('is_deleted', False), ('scope', 'daily')), fields=('class_section', 'session_date', 'scope'), name='uq_daily_attendance_class_date'),
        ),
        migrations.AddConstraint(
            model_name='attendancesession',
            constraint=models.UniqueConstraint(condition=models.Q(('is_deleted', False), ('scope', 'period')), fields=('class_section', 'session_date', 'period_number', 'scope'), name='uq_period_attendance_class_date_number'),
        ),
        migrations.AddIndex(
            model_name='attendancerecord',
            index=models.Index(fields=['session', 'status'], name='attendance__session_8dae34_idx'),
        ),
        migrations.AddIndex(
            model_name='attendancerecord',
            index=models.Index(fields=['enrollment', 'status'], name='attendance__enrollm_308d93_idx'),
        ),
        migrations.AddIndex(
            model_name='attendancerecord',
            index=models.Index(fields=['excuse_status', 'updated_at'], name='attendance__excuse__2d5dc4_idx'),
        ),
        migrations.AddConstraint(
            model_name='attendancerecord',
            constraint=models.UniqueConstraint(condition=models.Q(('is_deleted', False)), fields=('session', 'enrollment'), name='uq_attendance_record_session_enrollment'),
        ),
        migrations.AddIndex(
            model_name='parentnotification',
            index=models.Index(fields=['school', 'status', 'created_at'], name='attendance__school__3b236f_idx'),
        ),
        migrations.AddIndex(
            model_name='parentnotification',
            index=models.Index(fields=['guardian', 'created_at'], name='attendance__guardia_cd2f3b_idx'),
        ),
        migrations.AddIndex(
            model_name='parentnotification',
            index=models.Index(fields=['channel', 'status'], name='attendance__channel_00af45_idx'),
        ),
    ]
