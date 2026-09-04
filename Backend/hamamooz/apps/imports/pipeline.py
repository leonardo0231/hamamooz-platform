from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import services
from .comprehensive_flexible import validate_flexible_hardened_comprehensive_workbook
from .comprehensive_hardening import (
    apply_hardened_comprehensive_workbook,
    enrich_comprehensive_rows,
)
from .models import ImportJob


def process_import_job(job_id):
    """Process new comprehensive imports through the identity-aware flexible pipeline.

    Historical non-comprehensive jobs are still delegated to the legacy service so old failed
    jobs remain retryable, while the public serializer prevents creating new legacy imports.
    """

    probe = ImportJob.all_objects.get(pk=job_id)
    if probe.import_type != ImportJob.ImportType.COMPREHENSIVE_SCHOOL:
        return services.process_import_job(job_id)

    with transaction.atomic():
        job = ImportJob.objects.select_for_update().get(pk=job_id)
        stale_before = timezone.now() - timedelta(
            minutes=getattr(settings, "IMPORT_PROCESSING_TIMEOUT_MINUTES", 30)
        )
        if job.status == ImportJob.Status.PROCESSING:
            if job.started_at and job.started_at >= stale_before:
                return job
        elif job.status not in [ImportJob.Status.QUEUED, ImportJob.Status.FAILED]:
            return job

        job.status = ImportJob.Status.PROCESSING
        job.started_at = timezone.now()
        job.finished_at = None
        job.successful_rows = 0
        job.error_count = 0
        job.errors = []
        job.result_summary = {}
        job.save(
            update_fields=[
                "status",
                "started_at",
                "finished_at",
                "successful_rows",
                "error_count",
                "errors",
                "result_summary",
                "updated_at",
            ]
        )

    try:
        loaded = enrich_comprehensive_rows(job, services._load_rows(job))
        prepared, errors = validate_flexible_hardened_comprehensive_workbook(job, loaded.rows)
        if errors:
            with transaction.atomic():
                locked_job = ImportJob.objects.select_for_update().get(pk=job_id)
                if locked_job.status == ImportJob.Status.CANCELLED:
                    return locked_job
                locked_job.status = ImportJob.Status.FAILED
                locked_job.total_rows = loaded.source_row_count
                locked_job.error_count = len(errors)
                locked_job.errors = errors[:1000]
                locked_job.result_summary = {
                    "warning_count": len(prepared.get("warnings", [])),
                    "normalization_warnings": prepared.get("warnings", [])[:1000],
                }
                locked_job.finished_at = timezone.now()
                locked_job.save()
                return locked_job

        with transaction.atomic():
            locked_job = ImportJob.objects.select_for_update().get(pk=job_id)
            if locked_job.status == ImportJob.Status.CANCELLED:
                return locked_job
            summary = apply_hardened_comprehensive_workbook(locked_job, prepared)
            warnings = prepared.get("warnings", [])
            summary["warning_count"] = len(warnings)
            summary["normalization_warnings"] = warnings[:1000]
            locked_job.status = ImportJob.Status.COMPLETED
            locked_job.total_rows = loaded.source_row_count
            locked_job.successful_rows = loaded.source_row_count
            locked_job.error_count = 0
            locked_job.errors = []
            locked_job.result_summary = summary
            locked_job.finished_at = timezone.now()
            locked_job.save()
            return locked_job
    except OSError:
        job.status = ImportJob.Status.QUEUED
        job.save(update_fields=["status", "updated_at"])
        raise
    except Exception as exc:
        with transaction.atomic():
            locked_job = ImportJob.objects.select_for_update().get(pk=job_id)
            if locked_job.status == ImportJob.Status.CANCELLED:
                return locked_job
            locked_job.status = ImportJob.Status.FAILED
            locked_job.error_count = 1
            locked_job.errors = [{"row": None, "message": str(exc)[:2000]}]
            locked_job.result_summary = {}
            locked_job.finished_at = timezone.now()
            locked_job.save()
            return locked_job
