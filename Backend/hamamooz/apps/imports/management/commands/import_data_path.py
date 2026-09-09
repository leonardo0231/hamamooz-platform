import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from hamamooz.apps.accounts.models import User
from hamamooz.apps.imports.models import DataPathImport
from hamamooz.apps.imports.services.data_path import discover_data_path, process_data_path_import
from hamamooz.apps.organizations.models import Organization, School


class Command(BaseCommand):
    help = "Scan the mounted Data/Excel and Data/Photo tree and create report cards."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", required=True)
        parser.add_argument("--school-id", required=True)
        parser.add_argument("--requested-by", required=True, help="User UUID that owns the run.")
        parser.add_argument("--data-root", default=str(settings.DATA_ROOT))
        parser.add_argument("--month", type=int, choices=range(1, 13), default=None)
        parser.add_argument("--overwrite-photos", action="store_true")
        parser.add_argument("--no-reports", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        root = Path(options["data_root"]).expanduser().resolve()
        if options["dry_run"]:
            try:
                manifest = discover_data_path(root)
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(json.dumps(manifest, ensure_ascii=False, indent=2))
            return

        try:
            organization = Organization.objects.get(pk=options["organization_id"])
            school = School.objects.get(pk=options["school_id"], organization=organization)
            requested_by = User.objects.get(pk=options["requested_by"])
        except (Organization.DoesNotExist, School.DoesNotExist, User.DoesNotExist, ValueError, TypeError) as exc:
            raise CommandError("سازمان، مدرسه یا کاربر درخواست‌دهنده پیدا نشد.") from exc

        run = DataPathImport.objects.create(
            organization=organization,
            school=school,
            requested_by=requested_by,
            source_root=str(root),
            overwrite_photos=options["overwrite_photos"],
            generate_reports=not options["no_reports"],
            report_month=options["month"],
        )
        result = process_data_path_import(run.id)
        self.stdout.write(
            json.dumps(
                {
                    "id": str(result.id),
                    "status": result.status,
                    "summary": result.result_summary,
                    "errors": result.errors,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
