from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from hamamooz.apps.attendance.models import AbsenceEvidence
from hamamooz.apps.imports.models import ImportJob
from hamamooz.apps.reports.models import ReportArchive


class Command(BaseCommand):
    help = "حذف فایل‌های منقضی‌شده طبق سیاست نگهداری؛ پیش‌فرض فقط گزارش می‌دهد"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        now = timezone.now()
        policies = [
            (
                ImportJob.all_objects.filter(
                    created_at__lt=now - timedelta(days=settings.IMPORT_FILE_RETENTION_DAYS)
                ),
                "source_file",
            ),
            (
                ReportArchive.all_objects.filter(
                    created_at__lt=now - timedelta(days=settings.REPORT_FILE_RETENTION_DAYS)
                ),
                "output_file",
            ),
            (
                AbsenceEvidence.objects.filter(
                    created_at__lt=now - timedelta(days=settings.EVIDENCE_FILE_RETENTION_DAYS)
                ),
                "file",
            ),
        ]
        candidates = []
        for queryset, field_name in policies:
            for obj in queryset.iterator():
                field = getattr(obj, field_name)
                if field and field.name:
                    candidates.append((obj, field_name, field.name))
        if not options["apply"]:
            self.stdout.write(f"{len(candidates)} فایل کاندید حذف است؛ برای اجرا --apply بزنید.")
            return
        deleted = 0
        for obj, field_name, name in candidates:
            field = getattr(obj, field_name)
            field.storage.delete(name)
            setattr(obj, field_name, "")
            obj.save(update_fields=[field_name, "updated_at"])
            deleted += 1
        self.stdout.write(self.style.SUCCESS(f"{deleted} فایل حذف شد."))
