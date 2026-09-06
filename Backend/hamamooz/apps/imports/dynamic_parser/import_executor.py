from collections import Counter

from .import_report import ImportReport


class DynamicImportExecutor:
    """Execution layer for mapped workbook data.

    The first stage is intentionally preview-only. It produces a deterministic
    import report before database writes so malformed workbooks cannot partially
    modify school data.
    """

    def execute_preview(self, workbook_schema):
        report = ImportReport(file_name=workbook_schema.file_name)
        report.sheets = workbook_schema.sheets
        report.indicators_detected = list(dict.fromkeys(workbook_schema.indicators))
        report.periods_detected = list(dict.fromkeys(workbook_schema.periods))
        report.students_detected = len(workbook_schema.students)

        duplicates = [
            code for code, count in Counter(
                item.get("national_code") for item in workbook_schema.students
                if item.get("national_code")
            ).items()
            if count > 1
        ]
        if duplicates:
            report.add_warning(
                f"Duplicate student identifiers detected: {len(duplicates)}"
            )

        if not report.indicators_detected:
            report.add_warning("No assessment indicators detected in workbook.")

        if not report.periods_detected:
            report.add_warning("No assessment periods detected in workbook.")

        return report
