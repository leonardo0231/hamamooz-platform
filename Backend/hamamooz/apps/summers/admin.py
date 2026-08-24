from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import transaction

from hamamooz.apps.core.services import record_audit

from .models import (
    SummerComprehensiveExam,
    SummerCourse,
    SummerCourseRegistration,
    SummerProgram,
    SummerProgramRevision,
    SummerRegistration,
    SummerSubjectScore,
)


class FrozenSummerRosterAdminMixin:
    """Keep Django administration subject to the same finalized-roster boundary."""

    immutable_roster_fields = ()

    @staticmethod
    def roster_program(obj):
        return obj.program if hasattr(obj, "program") else obj.registration.program

    def has_change_permission(self, request, obj=None):
        if obj and self.roster_program(obj).exams.filter(
            status=SummerComprehensiveExam.Status.FINALIZED
        ).exists():
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and self.roster_program(obj).exams.filter(
            status=SummerComprehensiveExam.Status.FINALIZED
        ).exists():
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        fields = tuple(super().get_readonly_fields(request, obj))
        if obj:
            fields += tuple(self.immutable_roster_fields)
        return fields

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            program = SummerProgram.objects.select_for_update().get(
                pk=self.roster_program(obj).pk
            )
            if program.exams.filter(status=SummerComprehensiveExam.Status.FINALIZED).exists():
                raise PermissionDenied("فهرست برنامه دارای آزمون جامع نهایی‌شده قابل تغییر نیست.")
            obj.full_clean()
            super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        with transaction.atomic():
            program = SummerProgram.objects.select_for_update().get(
                pk=self.roster_program(obj).pk
            )
            if program.exams.filter(status=SummerComprehensiveExam.Status.FINALIZED).exists():
                raise PermissionDenied("فهرست برنامه دارای آزمون جامع نهایی‌شده قابل تغییر نیست.")
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            for item in queryset:
                self.delete_model(request, item)


@admin.register(SummerProgram)
class SummerProgramAdmin(admin.ModelAdmin):
    list_display = ["title", "school", "academic_year", "pass_threshold", "is_deleted"]
    list_filter = ["school", "academic_year", "is_deleted"]
    search_fields = ["title", "school__name"]

    def save_model(self, request, obj, form, change):
        old_threshold = None
        if change:
            old_threshold = (
                SummerProgram.all_objects.only("pass_threshold").get(pk=obj.pk).pass_threshold
            )
        super().save_model(request, obj, form, change)
        if change and old_threshold != obj.pass_threshold:
            SummerProgramRevision.objects.create(
                program=obj,
                actor=request.user,
                old_pass_threshold=old_threshold,
                new_pass_threshold=obj.pass_threshold,
                reason="تغییر حد قبولی از پنل مدیریت Django",
            )
            record_audit(
                action="summer_program.threshold_changed",
                actor=request.user,
                request=request,
                entity=obj,
                organization_id=obj.organization_id,
                school_id=obj.school_id,
                changes={
                    "before": {
                        "pass_threshold": (
                            str(old_threshold) if old_threshold is not None else None
                        )
                    },
                    "after": {
                        "pass_threshold": (
                            str(obj.pass_threshold) if obj.pass_threshold is not None else None
                        )
                    },
                },
            )


@admin.register(SummerProgramRevision)
class SummerProgramRevisionAdmin(admin.ModelAdmin):
    list_display = [
        "program",
        "old_pass_threshold",
        "new_pass_threshold",
        "actor",
        "created_at",
    ]
    readonly_fields = [
        "program",
        "actor",
        "old_pass_threshold",
        "new_pass_threshold",
        "reason",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SummerCourse)
class SummerCourseAdmin(FrozenSummerRosterAdminMixin, admin.ModelAdmin):
    immutable_roster_fields = ("program", "subject")
    list_display = ["program", "subject", "is_deleted"]
    list_filter = ["program__school", "program__academic_year", "is_deleted"]


@admin.register(SummerRegistration)
class SummerRegistrationAdmin(FrozenSummerRosterAdminMixin, admin.ModelAdmin):
    immutable_roster_fields = ("program", "enrollment")
    list_display = ["program", "enrollment", "is_deleted"]
    list_filter = ["program__school", "program__academic_year", "is_deleted"]


@admin.register(SummerCourseRegistration)
class SummerCourseRegistrationAdmin(FrozenSummerRosterAdminMixin, admin.ModelAdmin):
    immutable_roster_fields = ("registration", "course")
    list_display = ["registration", "course", "is_deleted"]
    list_filter = ["registration__program__school", "is_deleted"]


@admin.register(SummerComprehensiveExam)
class SummerComprehensiveExamAdmin(admin.ModelAdmin):
    list_display = ["title", "program", "exam_date", "status", "is_deleted"]
    list_filter = ["program__school", "status", "is_deleted"]
    readonly_fields = ["status", "finalized_at", "finalized_by"]


@admin.register(SummerSubjectScore)
class SummerSubjectScoreAdmin(admin.ModelAdmin):
    list_display = ["exam", "course_registration", "value", "recorded_by", "updated_at"]
    list_filter = ["exam__program__school", "exam"]
    readonly_fields = [
        "exam",
        "course_registration",
        "value",
        "recorded_by",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
