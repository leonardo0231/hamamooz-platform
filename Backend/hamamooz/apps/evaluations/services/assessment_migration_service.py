from typing import Iterable


class AssessmentMigrationService:
    """Bridge helper for migrating legacy evaluations into dynamic assessments.

    This service intentionally keeps migration logic separate from models so the
    legacy MonthlyEvaluation flow can coexist while data is moved gradually.
    """

    def convert_monthly_evaluation(self, evaluation) -> dict:
        return {
            "student": getattr(evaluation.enrollment, "student_id", None),
            "period": {
                "legacy_month": evaluation.month_no,
            },
            "metrics": [
                {
                    "code": metric.metric_code,
                    "score": metric.value,
                }
                for metric in evaluation.metric_scores.all()
            ],
        }

    def convert_queryset(self, evaluations: Iterable) -> list[dict]:
        return [self.convert_monthly_evaluation(item) for item in evaluations]
