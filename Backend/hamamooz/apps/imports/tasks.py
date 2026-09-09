from celery import shared_task

from .pipeline import process_import_job
from .services import mark_import_job_failed
from .services.data_path import process_data_path_import


@shared_task(bind=True, max_retries=3)
def process_import_job_task(self, job_id):
    try:
        job = process_import_job(job_id)
    except OSError as exc:
        if self.request.retries >= self.max_retries:
            mark_import_job_failed(job_id, exc)
            raise
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
    return {"status": job.status, "successful_rows": job.successful_rows, "errors": job.error_count}


@shared_task(bind=True, max_retries=2)
def process_data_path_import_task(self, run_id):
    try:
        run = process_data_path_import(run_id)
    except OSError as exc:
        if self.request.retries >= self.max_retries:
            raise
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
    return {
        "status": run.status,
        "summary": run.result_summary,
        "errors": len(run.errors or []),
    }
