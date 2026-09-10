import json

from django.core.management.base import BaseCommand, CommandError

from hamamooz.apps.imports.data_directory import DataDirectoryScanner
from hamamooz.apps.imports.defaults import get_besat_organization
from hamamooz.apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Scan Data/Excel workbooks into raw, normalized, provenance-preserving manifests."

    def add_arguments(self, parser):
        parser.add_argument(
            "--directory",
            help="Optional Data/Excel directory. Defaults to HAMAMOOZ_DATA_DIRECTORY or repository Data/Excel.",
        )

    def handle(self, *args, **options):
        try:
            school = get_besat_organization()
        except Organization.DoesNotExist as exc:
            raise CommandError("مدرسه بعثت برای اسکن داده پیکربندی نشده است.") from exc
        try:
            result = DataDirectoryScanner(school, options.get("directory")).scan()
        except (FileNotFoundError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, default=str))
