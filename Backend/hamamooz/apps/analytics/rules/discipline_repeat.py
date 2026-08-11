from datetime import timedelta

from django.utils import timezone

from hamamooz.apps.behavior.models import BehaviorEvent

from .base import BaseRiskRule, SignalCandidate


class DisciplineRepeatRule(BaseRiskRule):
    code = "discipline_repeat"
    version = 1
    default_parameters = {"window_days": 60, "minimum_count": 3}

    def evaluate(self, enrollment, parameters):
        days = int(parameters.get("window_days", self.default_parameters["window_days"]))
        minimum = int(parameters.get("minimum_count", self.default_parameters["minimum_count"]))
        start = timezone.now() - timedelta(days=days)
        events = BehaviorEvent.objects.filter(
            enrollment=enrollment,
            polarity=BehaviorEvent.Polarity.NEGATIVE,
            status__in=[
                BehaviorEvent.Status.CONFIRMED,
                BehaviorEvent.Status.UNDER_FOLLOW_UP,
                BehaviorEvent.Status.RESOLVED,
            ],
            occurred_at__gte=start,
        )
        count = events.count()
        if count < minimum:
            return []
        return [
            SignalCandidate(
                severity="high",
                evidence={"negative_confirmed_event_count": count},
                explanation=f"{count} confirmed negative behavior events require follow-up.",
                window={"days": days, "start": start.date().isoformat()},
            )
        ]
