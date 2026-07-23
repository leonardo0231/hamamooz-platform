import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from .models import ParentNotification

logger = logging.getLogger(__name__)


class SMSBackendError(RuntimeError):
    pass


class NotificationDispatchError(RuntimeError):
    pass


class BaseSMSBackend:
    def send(self, *, recipient, message, metadata=None):
        raise NotImplementedError


class DisabledSMSBackend(BaseSMSBackend):
    def send(self, *, recipient, message, metadata=None):
        raise SMSBackendError("سرویس پیامک برای محیط فعلی پیکربندی نشده است.")


class ConsoleSMSBackend(BaseSMSBackend):
    def send(self, *, recipient, message, metadata=None):
        masked = f"***{recipient[-4:]}" if recipient else ""
        logger.info(
            "attendance_sms_console",
            extra={
                "recipient_masked": masked,
                "message_length": len(message or ""),
                "notification_id": (metadata or {}).get("notification_id"),
            },
        )
        return True


def get_sms_backend():
    backend_path = getattr(
        settings,
        "ATTENDANCE_SMS_BACKEND",
        "hamamooz.apps.attendance.notifications.DisabledSMSBackend",
    )
    return import_string(backend_path)()


def _terminal_status(status):
    return status in {
        ParentNotification.Status.SENT,
        ParentNotification.Status.SKIPPED,
        ParentNotification.Status.DEAD_LETTER,
    }


def _claim_notification(notification_id):
    max_attempts = getattr(settings, "ATTENDANCE_NOTIFICATION_MAX_ATTEMPTS", 5)
    stale_after = timedelta(minutes=getattr(settings, "ATTENDANCE_NOTIFICATION_STALE_MINUTES", 15))
    with transaction.atomic():
        notification = ParentNotification.objects.select_for_update().get(pk=notification_id)
        if _terminal_status(notification.status):
            return None
        if (
            notification.status == ParentNotification.Status.PROCESSING
            and notification.updated_at >= timezone.now() - stale_after
        ):
            return None
        if notification.next_attempt_at and notification.next_attempt_at > timezone.now():
            return None
        if notification.attempts >= max_attempts:
            notification.status = ParentNotification.Status.DEAD_LETTER
            notification.last_error = notification.last_error or "حداکثر تلاش ارسال انجام شد."
            notification.save(update_fields=["status", "last_error", "updated_at"])
            return None
        notification.status = ParentNotification.Status.PROCESSING
        notification.attempts += 1
        notification.next_attempt_at = None
        notification.save(update_fields=["status", "attempts", "next_attempt_at", "updated_at"])
        return notification


def dispatch_notification(notification):
    notification_id = getattr(notification, "pk", notification)
    claimed = _claim_notification(notification_id)
    if claimed is None:
        return ParentNotification.objects.get(pk=notification_id)
    notification = claimed

    if notification.channel == ParentNotification.Channel.IN_APP:
        notification.status = ParentNotification.Status.SKIPPED
        notification.last_error = (
            "پرتال والدین در نسخه فعلی فعال نیست؛ کانال ایمیل یا پیامک انتخاب شود."
        )
        notification.save(update_fields=["status", "last_error", "updated_at"])
        return notification

    if not notification.recipient:
        notification.status = ParentNotification.Status.SKIPPED
        notification.last_error = "گیرنده برای کانال انتخاب‌شده ثبت نشده است."
        notification.save(update_fields=["status", "last_error", "updated_at"])
        return notification

    try:
        if notification.channel == ParentNotification.Channel.EMAIL:
            send_mail(
                notification.subject,
                notification.message,
                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                [notification.recipient],
                fail_silently=False,
            )
        elif notification.channel == ParentNotification.Channel.SMS:
            metadata = dict(notification.metadata or {})
            metadata["notification_id"] = str(notification.id)
            get_sms_backend().send(
                recipient=notification.recipient,
                message=notification.message,
                metadata=metadata,
            )
        else:
            raise ValueError("کانال ارسال ناشناخته است.")
    except Exception as exc:
        delay_minutes = min(60, 2 ** max(notification.attempts - 1, 0))
        with transaction.atomic():
            locked = ParentNotification.objects.select_for_update().get(pk=notification.id)
            max_attempts = getattr(settings, "ATTENDANCE_NOTIFICATION_MAX_ATTEMPTS", 5)
            locked.status = (
                ParentNotification.Status.DEAD_LETTER
                if locked.attempts >= max_attempts
                else ParentNotification.Status.FAILED
            )
            locked.next_attempt_at = (
                None
                if locked.status == ParentNotification.Status.DEAD_LETTER
                else timezone.now() + timedelta(minutes=delay_minutes)
            )
            locked.last_error = str(exc)[:2000]
            locked.save(
                update_fields=[
                    "status",
                    "next_attempt_at",
                    "last_error",
                    "updated_at",
                ]
            )
        logger.exception(
            "attendance_notification_failed",
            extra={"notification_id": str(notification.id)},
        )
        raise NotificationDispatchError(str(exc)) from exc

    notification.mark_sent()
    return notification
