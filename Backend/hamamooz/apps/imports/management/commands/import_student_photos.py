import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from hamamooz.apps.imports.services.photo_importer import StudentPhotoImporter
from hamamooz.apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Preview or import student photos named by national ID."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            required=True,
            help="Organization UUID whose students may receive the photos.",
        )
        source = parser.add_mutually_exclusive_group(required=True)
        source.add_argument(
            "--directory",
            help="Mounted Data/Photo directory to scan recursively.",
        )
        source.add_argument("--zip", dest="zip_path", help="Photo ZIP archive to scan.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Audit matches without writing student photos.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace an existing student photo (never enabled implicitly).",
        )

    def handle(self, *args, **options):
        try:
            organization = Organization.objects.get(pk=options["organization_id"])
        except (Organization.DoesNotExist, ValueError, TypeError) as exc:
            raise CommandError("Organization was not found.") from exc

        directory = options.get("directory")
        zip_path = options.get("zip_path")
        if directory and not Path(directory).is_dir():
            raise CommandError("Photo directory does not exist.")
        if zip_path and not Path(zip_path).is_file():
            raise CommandError("Photo ZIP archive does not exist.")

        importer = StudentPhotoImporter(organization)
        try:
            if directory:
                result = importer.import_directory(
                    directory,
                    dry_run=options["dry_run"],
                    overwrite=options["overwrite"],
                )
            else:
                result = importer.import_zip(
                    zip_path,
                    dry_run=options["dry_run"],
                    overwrite=options["overwrite"],
                )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        payload = {
            "organization_id": str(organization.id),
            "source": str(directory or zip_path),
            "dry_run": options["dry_run"],
            "overwrite": options["overwrite"],
            "result": result,
        }
        self.stdout.write(json.dumps(payload, ensure_ascii=False))
