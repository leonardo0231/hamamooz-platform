from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from hamamooz.apps.imports.models import ImportJob
from hamamooz.apps.imports.services import EXPECTED_HEADERS


class Command(BaseCommand):
    help = "Generate the three fixed XLSX templates used by the MVP import process."

    def handle(self, *args, **options):
        target = Path(settings.BASE_DIR) / "docs" / "import_templates"
        target.mkdir(parents=True, exist_ok=True)
        examples = {
            ImportJob.ImportType.STUDENTS: ["0012345678", "علی", "احمدی", "2012-09-05", "male"],
            ImportJob.ImportType.ENROLLMENTS: [
                "0012345678",
                "1405-1406",
                "grade-7",
                "7-a",
                "1001",
                "2026-09-23",
            ],
            ImportJob.ImportType.SCORES: [
                "00000000-0000-0000-0000-000000000000",
                "0012345678",
                18.5,
                "present",
                "",
            ],
        }
        for import_type, headers in EXPECTED_HEADERS.items():
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = import_type
            sheet.append(headers)
            sheet.append(examples[import_type])
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="2563EB")
                cell.alignment = Alignment(horizontal="center")
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column in sheet.columns:
                letter = column[0].column_letter
                sheet.column_dimensions[letter].width = max(
                    16, max(len(str(c.value or "")) for c in column) + 2
                )
            path = target / f"{import_type}_template.xlsx"
            workbook.save(path)
            self.stdout.write(self.style.SUCCESS(str(path)))
