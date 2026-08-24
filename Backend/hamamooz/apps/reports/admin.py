from django.contrib import admin

from .models import ReportArchive, ReportDraft, ReportTemplate


@admin.register(ReportArchive)
class ReportArchiveAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "school",
        "layout_key",
        "report_type",
        "report_version",
        "status",
        "requested_by",
    )
    list_filter = ("layout_key", "report_type", "status", "school")
    readonly_fields = (
        "snapshot",
        "status",
        "source_fingerprint",
        "tracking_code",
        "report_version",
        "formula_version",
        "error_message",
    )


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "school", "layout_key", "report_type", "is_active")
    list_filter = ("layout_key", "report_type", "is_active")


@admin.register(ReportDraft)
class ReportDraftAdmin(admin.ModelAdmin):
    list_display = ("created_at", "school", "layout_key", "status", "created_by")
    list_filter = ("layout_key", "status", "school")
    readonly_fields = (
        "snapshot",
        "status",
        "source_fingerprint",
        "tracking_code",
        "report_version",
    )
