from django.contrib import admin

from .models import ReportArchive


@admin.register(ReportArchive)
class ReportArchiveAdmin(admin.ModelAdmin):
    list_display = ("created_at", "school", "report_type", "status", "requested_by")
    list_filter = ("report_type", "status", "school")
    readonly_fields = ("snapshot", "formula_version", "error_message")
