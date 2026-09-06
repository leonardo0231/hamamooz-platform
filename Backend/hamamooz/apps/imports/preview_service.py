from dataclasses import dataclass, field

from .models import ImportJob


@dataclass
class ImportPreviewResult:
    students: int = 0
    classes: list[str] = field(default_factory=list)
    indicators: int = 0
    periods: int = 0
    warnings: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

    def as_dict(self):
        return {
            "summary": {
                "students": self.students,
                "classes": self.classes,
                "indicators": self.indicators,
                "periods": self.periods,
            },
            "warnings": self.warnings,
            "errors": self.errors,
        }


class ImportPreviewService:
    """
    Read-only analysis stage before committing an import.

    This service must never create Student, Enrollment or AssessmentRecord
    objects. It only analyses the uploaded workbook and returns a preview.
    """

    def __init__(self, job: ImportJob):
        self.job = job

    def run(self):
        result = ImportPreviewResult()

        if not self.job.source_file:
            result.errors.append({
                "level": "error",
                "message": "Import file is missing",
            })
            return result.as_dict()

        # Workbook parser integration is deliberately separated from the
        # service. The next patch connects this to WorkbookSchema and the
        # dynamic parser pipeline.
        return result.as_dict()
