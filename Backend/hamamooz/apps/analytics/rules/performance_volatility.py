from statistics import pstdev

from hamamooz.apps.academics.models import TermResult

from .base import BaseRiskRule, SignalCandidate


class PerformanceVolatilityRule(BaseRiskRule):
    code = "performance_volatility"
    version = 1
    default_parameters = {"minimum_standard_deviation": 2.0, "window_terms": 3}

    def evaluate(self, enrollment, parameters):
        window_terms = int(parameters.get("window_terms", self.default_parameters["window_terms"]))
        minimum = float(
            parameters.get(
                "minimum_standard_deviation", self.default_parameters["minimum_standard_deviation"]
            )
        )
        values = list(
            TermResult.objects.filter(
                enrollment__student_id=enrollment.student_id, average__isnull=False
            )
            .select_related("term")
            .order_by("-term__starts_on")[:window_terms]
        )
        if len(values) < 3:
            return []
        averages = [float(result.average) for result in values]
        deviation = pstdev(averages)
        if deviation < minimum:
            return []
        return [
            SignalCandidate(
                severity="medium",
                evidence={"averages": averages, "standard_deviation": round(deviation, 4)},
                explanation="Term performance is materially volatile across the recent window.",
                window={"terms": len(values)},
            )
        ]
