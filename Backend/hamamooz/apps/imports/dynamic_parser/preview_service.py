from .import_report import ImportReport
from .workbook_detector import analyze_workbook
from .validator import DynamicImportValidator


class DynamicImportPreviewService:
    """Read-only import analysis before committing data."""

    def __init__(self, workbook):
        self.workbook = workbook

    def run(self):
        schema = analyze_workbook(self.workbook)
        report = ImportReport(file_name=schema.file_name)
        report.sheets = schema.sheets
        report.students_detected = len(schema.students)
        report.indicators_detected = schema.indicators
        report.periods_detected = schema.periods

        validator = DynamicImportValidator()
        mapped = {
            "national_code": any(
                "کد ملی" in column for columns in schema.columns.values() for column in columns
            )
        }
        validation = validator.validate_headers(mapped)

        for issue in validation.errors:
            report.add_error(issue.message)
        for issue in validation.warnings:
            report.add_warning(issue.message)

        return report
