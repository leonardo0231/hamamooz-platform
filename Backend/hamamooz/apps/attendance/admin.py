from django.contrib import admin

from .models import (
    AbsenceEvidence,
    AttendanceAlert,
    AttendancePolicy,
    AttendanceRecord,
    AttendanceRecordRevision,
    AttendanceSession,
    ParentNotification,
)


@admin.register(AttendancePolicy)
class AttendancePolicyAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "academic_year",
        "warning_absence_count",
        "critical_absence_count",
        "is_active",
    )
    list_filter = ("is_active", "academic_year")
    search_fields = ("school__name", "school__code")
    raw_id_fields = ("school", "academic_year")


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = (
        "class_section",
        "session_date",
        "scope",
        "period_number",
        "status",
        "taken_by",
    )
    list_filter = ("scope", "status", "school", "academic_year", "session_date")
    search_fields = ("class_section__title", "title")
    raw_id_fields = (
        "school",
        "academic_year",
        "class_section",
        "term",
        "course_offering",
        "taken_by",
        "finalized_by",
    )
    readonly_fields = ("finalized_at", "created_at", "updated_at")


class AbsenceEvidenceInline(admin.TabularInline):
    model = AbsenceEvidence
    extra = 0
    readonly_fields = (
        "original_name",
        "content_type",
        "size_bytes",
        "uploaded_by",
        "created_at",
    )


class AttendanceRecordRevisionInline(admin.TabularInline):
    model = AttendanceRecordRevision
    extra = 0
    can_delete = False
    readonly_fields = ("changed_by", "reason", "before", "after", "created_at")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "enrollment",
        "session",
        "status",
        "late_minutes",
        "early_leave_minutes",
        "excuse_status",
        "revision",
    )
    list_filter = ("status", "excuse_status", "session__scope", "session__session_date")
    search_fields = (
        "enrollment__student__national_id",
        "enrollment__student__first_name",
        "enrollment__student__last_name",
    )
    raw_id_fields = (
        "session",
        "enrollment",
        "recorded_by",
        "excuse_submitted_by",
        "reviewed_by",
    )
    readonly_fields = ("revision", "created_at", "updated_at")
    inlines = (AbsenceEvidenceInline, AttendanceRecordRevisionInline)


@admin.register(AttendanceAlert)
class AttendanceAlertAdmin(admin.ModelAdmin):
    list_display = (
        "enrollment",
        "school",
        "scope",
        "severity",
        "absence_count",
        "absence_percent",
        "status",
    )
    list_filter = ("scope", "severity", "status", "school", "academic_year")
    search_fields = (
        "enrollment__student__national_id",
        "enrollment__student__first_name",
        "enrollment__student__last_name",
    )
    raw_id_fields = (
        "policy",
        "school",
        "academic_year",
        "enrollment",
        "acknowledged_by",
        "resolved_by",
    )


@admin.register(ParentNotification)
class ParentNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "guardian",
        "kind",
        "channel",
        "status",
        "attempts",
        "created_at",
    )
    list_filter = ("kind", "channel", "status", "school")
    search_fields = (
        "student__first_name",
        "student__last_name",
        "guardian__first_name",
        "guardian__last_name",
        "recipient",
    )
    raw_id_fields = (
        "school",
        "student",
        "guardian",
        "attendance_record",
        "alert",
        "created_by",
    )
    readonly_fields = (
        "dedupe_key",
        "attempts",
        "sent_at",
        "last_error",
        "created_at",
        "updated_at",
    )
