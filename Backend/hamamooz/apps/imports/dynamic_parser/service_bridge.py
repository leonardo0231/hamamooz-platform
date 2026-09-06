"""
Bridge between the legacy import service and the new dynamic import pipeline.

This module intentionally does not remove the legacy importer yet. It provides a
safe migration point where new uploads can be analyzed before execution.
"""

from .workbook_detector import analyze_workbook
from .validator import DynamicImportValidator
from .import_report import ImportReport


class DynamicImportService:
    """High-level dynamic import workflow."""

    def __init__(self, workbook):
        self.workbook = workbook
        self.report = ImportReport()
        self.validator = DynamicImportValidator()

    def analyze(self):
        schema = analyze_workbook(self.workbook)
        self.report.schema = schema

        validation = self.validator.validate_schema(schema)
        self.report.validation = validation

        return self.report

    def can_execute(self):
        return not getattr(self.report, "errors", [])
