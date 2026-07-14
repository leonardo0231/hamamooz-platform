from celery import shared_task

from .services import process_import_job


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def process_import_job_task(job_id):
    job = process_import_job(job_id)
    return {"status": job.status, "successful_rows": job.successful_rows, "errors": job.error_count}
