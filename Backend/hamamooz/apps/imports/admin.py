from django.contrib import admin

from .models import DataPathImport, ImportJob


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "school",
        "import_type",
        "status",
        "successful_rows",
        "error_count",
    )
    list_filter = ("import_type", "status", "school")
    readonly_fields = ("checksum", "errors", "started_at", "finished_at")


@admin.register(DataPathImport)
class DataPathImportAdmin(admin.ModelAdmin):
    list_display = ("created_at", "school", "status", "report_month", "finished_at")
    list_filter = ("status", "school", "generate_reports")
    readonly_fields = ("manifest", "result_summary", "errors", "started_at", "finished_at")
