import json

from django.core.management.base import BaseCommand, CommandError

from hamamooz.apps.imports.data_directory import DataDirectoryScanner
from hamamooz.apps.organizations.models import School


class Command(BaseCommand):
    help = "Scan Data/Excel workbooks into raw, normalized, provenance-preserving manifests."

    def add_arguments(self, parser):
        parser.add_argument("--school", required=True, help="UUID or code of the target school")
        parser.add_argument(
            "--directory",
            help="Optional Data/Excel directory. Defaults to HAMAMOOZ_DATA_DIRECTORY or repository Data/Excel.",
        )

    def handle(self, *args, **options):
        school_value = options["school"].strip()
        school = School.objects.filter(pk=school_value).first() or School.objects.filter(
            code=school_value
        ).first()
        if school is None:
            raise CommandError("مدرسه با این شناسه یا کد پیدا نشد.")
        try:
            result = DataDirectoryScanner(school, options.get("directory")).scan()
        except (FileNotFoundError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, default=str))
