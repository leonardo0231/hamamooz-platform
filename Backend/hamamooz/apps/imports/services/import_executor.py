from django.db import transaction

from ..models import ImportJob


class ImportExecutor:
    """Coordinates confirmed workbook imports into domain writers."""

    def __init__(self, job: ImportJob):
        self.job = job
        self.summary = {
            "students": 0,
            "enrollments": 0,
            "indicators": 0,
            "records": 0,
        }

    @transaction.atomic
    def execute(self):
        self.job.status = ImportJob.Status.PROCESSING
        self.job.save(update_fields=["status", "updated_at"])

        # Writer hooks are intentionally isolated so legacy importers can be
        # replaced incrementally without changing ImportJob workflow.
        self.write_students()
        self.write_enrollments()
        self.write_indicators()
        self.write_records()

        self.job.status = ImportJob.Status.COMPLETED
        self.job.result_summary = self.summary
        self.job.save(update_fields=["status", "result_summary", "updated_at"])
        return self.summary

    def write_students(self):
        return None

    def write_enrollments(self):
        return None

    def write_indicators(self):
        return None

    def write_records(self):
        return None
