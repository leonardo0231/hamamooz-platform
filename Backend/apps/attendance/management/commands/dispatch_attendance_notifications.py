from django.core.management.base import BaseCommand
from hamamooz.apps.attendance.models import ParentNotification
from hamamooz.apps.attendance.notifications import dispatch_notification


class Command(BaseCommand):
    help = "ارسال مجدد اعلان‌های والدین که در صف یا ناموفق هستند"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        notifications = ParentNotification.objects.filter(
            status__in=[
                ParentNotification.Status.QUEUED,
                ParentNotification.Status.FAILED,
            ]
        ).order_by("created_at")[: options["limit"]]
        sent = 0
        for notification in notifications:
            dispatch_notification(notification)
            if notification.status == ParentNotification.Status.SENT:
                sent += 1
        self.stdout.write(self.style.SUCCESS(f"{sent} اعلان ارسال شد."))
