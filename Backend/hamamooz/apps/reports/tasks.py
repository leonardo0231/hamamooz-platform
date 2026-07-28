from celery import shared_task

from .services import generate_report


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def generate_report_task(report_id):
    report = generate_report(report_id)
    return {
        "status": report.status,
        "file": report.output_file.name if report.output_file else None,
    }
