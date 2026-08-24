from django.contrib import admin

from .models import (
    AcademicReportSettings,
    AcademicReportSettingsRevision,
    Assessment,
    AssessmentType,
    AnnualResult,
    AnnualSubjectResult,
    CalculationPolicy,
    CourseOffering,
    GradeSubject,
    Score,
    ScoreRevision,
    Subject,
    SubjectResult,
    TermResult,
)

admin.site.register(Subject)
admin.site.register(GradeSubject)
admin.site.register(CourseOffering)
admin.site.register(AssessmentType)
admin.site.register(Assessment)
admin.site.register(CalculationPolicy)
admin.site.register(SubjectResult)
admin.site.register(TermResult)
admin.site.register(AcademicReportSettings)
admin.site.register(AnnualResult)
admin.site.register(AnnualSubjectResult)


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ("assessment", "enrollment", "value", "status", "revision")
    readonly_fields = [field.name for field in Score._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ScoreRevision)
class ScoreRevisionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "score", "old_value", "new_value", "changed_by")
    readonly_fields = [field.name for field in ScoreRevision._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AcademicReportSettingsRevision)
class AcademicReportSettingsRevisionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "school", "academic_year", "revision", "changed_by")
    readonly_fields = [field.name for field in AcademicReportSettingsRevision._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
