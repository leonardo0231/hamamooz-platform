from celery import shared_task
from django.conf import settings

from .models import AttendancePolicy, ParentNotification
from .notifications import dispatch_notification
from .services import evaluate_policy_alerts


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def dispatch_parent_notification(notification_id):
    notification = ParentNotification.objects.get(pk=notification_id)
    if notification.status == ParentNotification.Status.SENT:
        return str(notification.id)
    dispatch_notification(notification)
    return str(notification.id)


@shared_task
def evaluate_attendance_alerts(policy_id=None):
    if not getattr(settings, "ATTENDANCE_AUTO_ALERTS_ENABLED", True) and not policy_id:
        return []
    policies = AttendancePolicy.objects.filter(is_active=True).select_related(
        "school", "academic_year"
    )
    if policy_id:
        policies = policies.filter(pk=policy_id)
    alert_ids = []
    for policy in policies:
        alert_ids.extend(
            str(alert.id) for alert in evaluate_policy_alerts(policy=policy)
        )
    return alert_ids
