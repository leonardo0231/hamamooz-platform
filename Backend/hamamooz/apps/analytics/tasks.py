from celery import shared_task

from .engine import run_for_enrollment
from .models import AnalyticsRun


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def run_targeted_analytics(self, enrollment_id):
    run = run_for_enrollment(
        enrollment_id=enrollment_id,
        trigger=AnalyticsRun.Trigger.DATA_MUTATION,
    )
    return str(run.id)


@shared_task
def reconcile_analytics():
    """Nightly reconciliation catches missed post-commit scheduling paths."""
    from hamamooz.apps.students.models import Enrollment

    return [
        run_targeted_analytics.delay(str(enrollment_id)).id
        for enrollment_id in Enrollment.objects.filter(status=Enrollment.Status.ACTIVE).values_list(
            "id", flat=True
        )
    ]
