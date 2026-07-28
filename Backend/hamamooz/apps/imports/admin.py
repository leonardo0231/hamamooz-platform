from django.contrib import admin

from .models import ImportJob


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
