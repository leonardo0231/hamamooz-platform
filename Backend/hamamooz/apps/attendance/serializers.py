from django.conf import settings
from rest_framework import serializers

from hamamooz.apps.accounts.access import (
    accessible_school_ids,
    allowed_class_ids,
    selected_school_ids,
)
from hamamooz.apps.students.models import Enrollment

from .models import (
    AbsenceEvidence,
    AttendanceAlert,
    AttendancePolicy,
    AttendanceRecord,
    AttendanceRecordRevision,
    AttendanceSession,
    ParentNotification,
)
from .permissions import can_manage_session


class AttendancePolicySerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source="school.name", read_only=True)
    academic_year_title = serializers.CharField(source="academic_year.title", read_only=True)

    class Meta:
        model = AttendancePolicy
        fields = [
            "id",
            "school",
            "school_name",
            "academic_year",
            "academic_year_title",
            "warning_absence_count",
            "critical_absence_count",
            "warning_absence_percent",
            "critical_absence_percent",
            "lookback_days",
            "include_excused_absences",
            "require_evidence_for_excuse",
            "notify_guardians",
            "notification_channels",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "school_name",
            "academic_year_title",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        if self.instance:
            immutable = {"school", "academic_year"}
            changed = {
                field
                for field in immutable
                if field in attrs and attrs[field] != getattr(self.instance, field)
            }
            if changed:
                raise serializers.ValidationError(
                    "شعبه و سال تحصیلی سیاست پس از ایجاد قابل تغییر نیستند."
                )
        school = attrs.get("school", getattr(self.instance, "school", None))
        if request and school and school.id not in set(accessible_school_ids(request.user)):
            raise serializers.ValidationError({"school": "به این شعبه دسترسی ندارید."})
        instance = self.instance or AttendancePolicy()
        for key, value in attrs.items():
            setattr(instance, key, value)
        instance.full_clean(exclude=["id"])
        return attrs


class AttendanceSessionSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source="school.name", read_only=True)
    class_title = serializers.CharField(source="class_section.title", read_only=True)
    subject_title = serializers.CharField(
        source="course_offering.grade_subject.subject.title", read_only=True
    )
    teacher_name = serializers.CharField(
        source="course_offering.teacher.get_full_name", read_only=True
    )
    taken_by_name = serializers.CharField(source="taken_by.get_full_name", read_only=True)
    record_count = serializers.IntegerField(source="records.count", read_only=True)

    class Meta:
        model = AttendanceSession
        fields = [
            "id",
            "school",
            "school_name",
            "academic_year",
            "class_section",
            "class_title",
            "term",
            "course_offering",
            "subject_title",
            "teacher_name",
            "session_date",
            "scope",
            "period_number",
            "title",
            "starts_at",
            "ends_at",
            "status",
            "taken_by",
            "taken_by_name",
            "finalized_by",
            "finalized_at",
            "notes",
            "record_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "taken_by",
            "taken_by_name",
            "finalized_by",
            "finalized_at",
            "record_count",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        if self.instance:
            structural = {
                "school",
                "academic_year",
                "class_section",
                "term",
                "course_offering",
                "session_date",
                "scope",
                "period_number",
            }
            changed = {
                field
                for field in structural
                if field in attrs and attrs[field] != getattr(self.instance, field)
            }
            if changed and (
                self.instance.status != AttendanceSession.Status.DRAFT
                or self.instance.records.exists()
            ):
                raise serializers.ValidationError(
                    "پس از ثبت رکورد، محدوده و تاریخ جلسه قابل تغییر نیست."
                )
        instance = self.instance or AttendanceSession()
        for key, value in attrs.items():
            setattr(instance, key, value)
        if request:
            school_ids = selected_school_ids(request)
            class_ids = allowed_class_ids(request.user, school_ids)
            if instance.school_id not in set(school_ids):
                raise serializers.ValidationError({"school": "به این شعبه دسترسی ندارید."})
            if instance.class_section_id not in set(class_ids):
                raise serializers.ValidationError({"class_section": "به این کلاس دسترسی ندارید."})
            instance.taken_by = getattr(self.instance, "taken_by", request.user)
            if not can_manage_session(request.user, instance):
                raise serializers.ValidationError("برای ایجاد یا ویرایش این جلسه دسترسی ندارید.")
        instance.full_clean(exclude=["id", "taken_by"] if not instance.taken_by_id else ["id"])
        return attrs


class AttendanceBulkItemSerializer(serializers.Serializer):
    enrollment = serializers.PrimaryKeyRelatedField(queryset=Enrollment.objects.all())
    status = serializers.ChoiceField(
        choices=[
            AttendanceRecord.Status.PRESENT,
            AttendanceRecord.Status.ABSENT_UNEXCUSED,
        ],
        default=AttendanceRecord.Status.PRESENT,
    )
    arrival_time = serializers.TimeField(required=False, allow_null=True)
    departure_time = serializers.TimeField(required=False, allow_null=True)
    late_minutes = serializers.IntegerField(required=False, min_value=0, max_value=1440, default=0)
    early_leave_minutes = serializers.IntegerField(
        required=False, min_value=0, max_value=1440, default=0
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=500, default="")

    def validate(self, attrs):
        if attrs["status"] != AttendanceRecord.Status.PRESENT:
            for field in ["arrival_time", "departure_time"]:
                if attrs.get(field):
                    raise serializers.ValidationError(
                        {field: "برای دانش‌آموز غایب زمان ورود یا خروج ثبت نمی‌شود."}
                    )
            if attrs.get("late_minutes") or attrs.get("early_leave_minutes"):
                raise serializers.ValidationError(
                    "برای دانش‌آموز غایب تأخیر یا خروج زودهنگام ثبت نمی‌شود."
                )
        return attrs


class BulkAttendanceSerializer(serializers.Serializer):
    records = AttendanceBulkItemSerializer(many=True, allow_empty=False)


class AbsenceEvidenceSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True)

    class Meta:
        model = AbsenceEvidence
        fields = [
            "id",
            "file",
            "original_name",
            "content_type",
            "size_bytes",
            "description",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
        ]
        read_only_fields = fields


class AttendanceRecordRevisionSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.get_full_name", read_only=True)

    class Meta:
        model = AttendanceRecordRevision
        fields = [
            "id",
            "changed_by",
            "changed_by_name",
            "reason",
            "before",
            "after",
            "created_at",
        ]
        read_only_fields = fields


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student = serializers.UUIDField(source="enrollment.student_id", read_only=True)
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)
    student_number = serializers.CharField(source="enrollment.student_number", read_only=True)
    class_title = serializers.CharField(source="session.class_section.title", read_only=True)
    session_date = serializers.DateField(source="session.session_date", read_only=True)
    session_scope = serializers.CharField(source="session.scope", read_only=True)
    subject_title = serializers.CharField(
        source="session.course_offering.grade_subject.subject.title", read_only=True
    )
    is_late = serializers.BooleanField(read_only=True)
    left_early = serializers.BooleanField(read_only=True)
    evidence_files = AbsenceEvidenceSerializer(many=True, read_only=True)
    history = AttendanceRecordRevisionSerializer(many=True, read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "session",
            "session_date",
            "session_scope",
            "enrollment",
            "student",
            "student_name",
            "student_number",
            "class_title",
            "subject_title",
            "status",
            "arrival_time",
            "departure_time",
            "late_minutes",
            "early_leave_minutes",
            "is_late",
            "left_early",
            "note",
            "absence_reason",
            "excuse_status",
            "excuse_submitted_by",
            "excuse_submitted_at",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "recorded_by",
            "revision",
            "evidence_files",
            "history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CorrectAttendanceRecordSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            AttendanceRecord.Status.PRESENT,
            AttendanceRecord.Status.ABSENT_UNEXCUSED,
        ],
        required=False,
    )
    arrival_time = serializers.TimeField(required=False, allow_null=True)
    departure_time = serializers.TimeField(required=False, allow_null=True)
    late_minutes = serializers.IntegerField(required=False, min_value=0, max_value=1440)
    early_leave_minutes = serializers.IntegerField(required=False, min_value=0, max_value=1440)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)
    reason = serializers.CharField(min_length=3, max_length=1000)


class SubmitAbsenceExcuseSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, max_length=2000)
    evidence_files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True,
        max_length=5,
        default=list,
    )

    def validate_evidence_files(self, files):
        maximum = int(getattr(settings, "ATTENDANCE_MAX_EVIDENCE_TOTAL_SIZE", 10 * 1024 * 1024))
        total = sum(getattr(item, "size", 0) for item in files)
        if total > maximum:
            raise serializers.ValidationError(
                f"مجموع حجم مدارک نباید بیشتر از {maximum // (1024 * 1024)} مگابایت باشد."
            )
        return files


class ReviewAbsenceExcuseSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")


class NotificationChannelsSerializer(serializers.Serializer):
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=ParentNotification.Channel.choices),
        required=False,
        allow_empty=False,
    )


class AttendanceAlertSerializer(serializers.ModelSerializer):
    student = serializers.UUIDField(source="enrollment.student_id", read_only=True)
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)
    class_title = serializers.CharField(source="enrollment.class_section.title", read_only=True)
    school_name = serializers.CharField(source="school.name", read_only=True)

    class Meta:
        model = AttendanceAlert
        fields = [
            "id",
            "policy",
            "school",
            "school_name",
            "academic_year",
            "enrollment",
            "student",
            "student_name",
            "class_title",
            "scope",
            "severity",
            "period_start",
            "period_end",
            "absence_count",
            "total_sessions",
            "absence_percent",
            "status",
            "acknowledged_by",
            "acknowledged_at",
            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ParentNotificationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    guardian_name = serializers.CharField(source="guardian.full_name", read_only=True)
    school_name = serializers.CharField(source="school.name", read_only=True)

    class Meta:
        model = ParentNotification
        fields = [
            "id",
            "school",
            "school_name",
            "student",
            "student_name",
            "enrollment",
            "guardian",
            "guardian_name",
            "attendance_record",
            "alert",
            "kind",
            "channel",
            "recipient",
            "subject",
            "message",
            "status",
            "attempts",
            "sent_at",
            "next_attempt_at",
            "last_error",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AttendanceReportQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    scope = serializers.ChoiceField(choices=AttendanceSession.Scope.choices, required=False)

    def validate(self, attrs):
        if (
            attrs.get("date_from")
            and attrs.get("date_to")
            and attrs["date_from"] > attrs["date_to"]
        ):
            raise serializers.ValidationError({"date_to": "پایان بازه باید بعد از شروع آن باشد."})
        return attrs


class StudentAttendanceReportQuerySerializer(AttendanceReportQuerySerializer):
    enrollment = serializers.PrimaryKeyRelatedField(queryset=Enrollment.objects.all())


class ClassAttendanceReportQuerySerializer(AttendanceReportQuerySerializer):
    class_section = serializers.UUIDField()
    academic_year = serializers.UUIDField(required=False)


class SchoolAttendanceReportQuerySerializer(AttendanceReportQuerySerializer):
    school = serializers.UUIDField()
    academic_year = serializers.UUIDField()


class NotifyGuardiansSerializer(StudentAttendanceReportQuerySerializer):
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=ParentNotification.Channel.choices),
        required=False,
        allow_empty=False,
    )
