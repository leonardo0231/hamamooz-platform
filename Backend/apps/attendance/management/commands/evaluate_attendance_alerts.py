from django.core.management.base import BaseCommand, CommandError
from hamamooz.apps.attendance.models import AttendancePolicy
from hamamooz.apps.attendance.services import evaluate_policy_alerts


class Command(BaseCommand):
    help = "محاسبه و به‌روزرسانی هشدارهای غیبت"

    def add_arguments(self, parser):
        parser.add_argument("--policy-id", dest="policy_id")

    def handle(self, *args, **options):
        policies = AttendancePolicy.objects.filter(is_active=True).select_related(
            "school", "academic_year"
        )
        if options["policy_id"]:
            policies = policies.filter(pk=options["policy_id"])
            if not policies.exists():
                raise CommandError("سیاست حضور و غیاب پیدا نشد.")
        count = 0
        for policy in policies:
            count += len(evaluate_policy_alerts(policy=policy))
        self.stdout.write(self.style.SUCCESS(f"{count} هشدار فعال محاسبه شد."))
