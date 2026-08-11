from hamamooz.apps.academics.models import Assessment, Score

from .base import BaseRiskRule, SignalCandidate


class MissingTeacherScoresRule(BaseRiskRule):
    code = "missing_teacher_scores"
    version = 1
    default_parameters = {"minimum_count": 1}

    def evaluate(self, enrollment, parameters):
        count = Score.objects.filter(
            enrollment=enrollment,
            status=Score.Status.NOT_ENTERED,
            assessment__status__in=[Assessment.Status.APPROVED, Assessment.Status.LOCKED],
        ).count()
        minimum = int(parameters.get("minimum_count", self.default_parameters["minimum_count"]))
        if count < minimum:
            return []
        return [
            SignalCandidate(
                severity="low",
                evidence={"missing_score_count": count},
                explanation="Approved assessments still contain missing scores for this student.",
                window={
                    "assessment_statuses": [Assessment.Status.APPROVED, Assessment.Status.LOCKED]
                },
            )
        ]
