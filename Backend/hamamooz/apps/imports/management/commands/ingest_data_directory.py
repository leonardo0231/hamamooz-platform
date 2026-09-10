import json

from django.core.management.base import BaseCommand, CommandError

from hamamooz.apps.imports.defaults import get_besat_organization
from hamamooz.apps.imports.direct_data_ingest import ingest_data_directory
from hamamooz.apps.organizations.models import Organization


class Command(BaseCommand):
    help = (
        "ثبت مستقیم فایل‌های Data/Excel در سامانه؛ ابتدا فایل‌های جامع و سپس "
        "سه کارنامه آزمون درسی را به‌صورت idempotent وارد می‌کند."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--excel-directory",
            dest="excel_directory",
            help="مسیر Data/Excel؛ در حالت پیش‌فرض از تنظیمات/ساختار مخزن پیدا می‌شود.",
        )
        parser.add_argument(
            "--photo-directory",
            dest="photo_directory",
            help="مسیر Data/Photo؛ در حالت پیش‌فرض کنار Data/Excel استفاده می‌شود.",
        )

    def handle(self, *args, **options):
        try:
            school = get_besat_organization()
        except Organization.DoesNotExist as exc:
            raise CommandError("مدرسه بعثت برای ورود مستقیم داده پیکربندی نشده است.") from exc
        try:
            result = ingest_data_directory(
                school,
                excel_directory=options.get("excel_directory"),
                photo_directory=options.get("photo_directory"),
            )
        except (FileNotFoundError, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, default=str))
