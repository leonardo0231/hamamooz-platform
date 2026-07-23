from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from hamamooz.apps.attendance.models import ParentNotification
from hamamooz.apps.attendance.tasks import dispatch_parent_notification


class Command(BaseCommand):
    help = "صف‌بندی مجدد اعلان‌های والدین که آماده تلاش بعدی هستند"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        notifications = ParentNotification.objects.filter(
            status__in=[
                ParentNotification.Status.QUEUED,
                ParentNotification.Status.FAILED,
            ]
        ).filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=timezone.now()))
        ids = list(
            notifications.order_by("created_at").values_list("id", flat=True)[: options["limit"]]
        )
        for notification_id in ids:
            dispatch_parent_notification.delay(str(notification_id))
        self.stdout.write(self.style.SUCCESS(f"{len(ids)} اعلان در صف ارسال قرار گرفت."))
