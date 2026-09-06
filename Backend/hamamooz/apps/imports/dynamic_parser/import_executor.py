from .import_report import ImportReport


class DynamicImportExecutor:
    """Execution layer for mapped workbook data.

    Keeps parsing and persistence separate so future database models can evolve
    without changing Excel analysis logic.
    """

    def execute_preview(self, workbook_schema):
        report = ImportReport(file_name=workbook_schema.file_name)
        report.sheets = workbook_schema.sheets
        report.indicators_detected = workbook_schema.indicators
        report.periods_detected = workbook_schema.periods
        report.students_detected = len(workbook_schema.students)
        return report
