from django.db.models import Avg

from hamamooz.apps.academics.models import TermResult

from .base import BaseRiskRule, SignalCandidate


class PeerPerformanceDropRule(BaseRiskRule):
    code = "peer_performance_drop"
    version = 1
    default_parameters = {"minimum_gap": 3.0}

    def evaluate(self, enrollment, parameters):
        latest = (
            TermResult.objects.filter(enrollment=enrollment, average__isnull=False)
            .select_related("term")
            .order_by("-term__starts_on")
            .first()
        )
        if not latest:
            return []
        peer_average = TermResult.objects.filter(
            term=latest.term,
            enrollment__class_section=enrollment.class_section,
            average__isnull=False,
        ).aggregate(value=Avg("average"))["value"]
        if peer_average is None:
            return []
        gap = float(peer_average - latest.average)
        minimum = float(parameters.get("minimum_gap", self.default_parameters["minimum_gap"]))
        if gap < minimum:
            return []
        return [
            SignalCandidate(
                severity="medium",
                evidence={
                    "student_average": float(latest.average),
                    "peer_average": float(peer_average),
                    "gap": round(gap, 4),
                },
                explanation="The latest term result is materially below the same-class peer average.",
                window={"term_id": str(latest.term_id), "cohort": "same_class"},
            )
        ]
