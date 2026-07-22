import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils.module_loading import import_string

from .models import ParentNotification

logger = logging.getLogger(__name__)


class SMSBackendError(RuntimeError):
    pass


class BaseSMSBackend:
    def send(self, *, recipient, message, metadata=None):
        raise NotImplementedError


class DisabledSMSBackend(BaseSMSBackend):
    def send(self, *, recipient, message, metadata=None):
        raise SMSBackendError("سرویس پیامک برای محیط فعلی پیکربندی نشده است.")


class ConsoleSMSBackend(BaseSMSBackend):
    def send(self, *, recipient, message, metadata=None):
        logger.info(
            "attendance_sms",
            extra={
                "recipient": recipient,
                "message": message,
                "metadata": metadata or {},
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


def dispatch_notification(notification):
    if notification.channel == ParentNotification.Channel.IN_APP:
        notification.mark_sent()
        return notification

    if not notification.recipient:
        notification.status = ParentNotification.Status.SKIPPED
        notification.last_error = "گیرنده برای کانال انتخاب‌شده ثبت نشده است."
        notification.save(update_fields=["status", "last_error", "updated_at"])
        return notification

    notification.attempts += 1
    notification.save(update_fields=["attempts", "updated_at"])
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
            get_sms_backend().send(
                recipient=notification.recipient,
                message=notification.message,
                metadata=notification.metadata,
            )
        else:
            raise ValueError("کانال ارسال ناشناخته است.")
    except Exception as exc:
        logger.exception(
            "attendance_notification_failed",
            extra={"notification_id": str(notification.id)},
        )
        notification.status = ParentNotification.Status.FAILED
        notification.last_error = str(exc)[:2000]
        notification.save(update_fields=["status", "last_error", "updated_at"])
        return notification

    notification.mark_sent()
    return notification
