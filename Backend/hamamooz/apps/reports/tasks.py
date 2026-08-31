from celery import shared_task

from .services import generate_report, render_report_batch


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def generate_report_task(report_id):
    report = generate_report(report_id)
    return {
        "status": report.status,
        "file": report.output_file.name if report.output_file else None,
    }


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def generate_report_batch_task(batch_id):
    batch = render_report_batch(batch_id)
    return {
        "status": batch.status,
        "completed": batch.completed_count,
        "failed": batch.failed_count,
    }
