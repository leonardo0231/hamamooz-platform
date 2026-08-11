from dataclasses import dataclass

from .models import Recommendation


@dataclass(frozen=True)
class RecommendationDraft:
    audience: str
    priority: str
    generated_text: str
    reason_snapshot: dict


class SignalSupportRule:
    """A deliberately small, versioned mapping rather than a user-authored DSL."""

    code = "signal_support"
    version = 1

    def applies_to(self, signal):
        return signal.rule_code in {
            "academic_drop",
            "multi_subject_drop",
            "high_unexcused_absence",
            "discipline_repeat",
            "performance_volatility",
            "peer_performance_drop",
        }

    def drafts_for(self, signal):
        if not self.applies_to(signal):
            return []
        snapshot = {
            "source_rule_code": signal.rule_code,
            "source_rule_version": signal.rule_version,
            "source_evidence": signal.evidence,
            "source_explanation": signal.explanation,
            "limitations": "Deterministic rule output; requires human review before release.",
        }
        priority = (
            signal.severity if signal.severity in Recommendation.Priority.values else "medium"
        )
        return [
            RecommendationDraft(
                audience=Recommendation.Audience.GUIDE_TEACHER,
                priority=priority,
                generated_text="Review the evidence with the student and agree a time-bounded educational follow-up.",
                reason_snapshot=snapshot,
            ),
            RecommendationDraft(
                audience=Recommendation.Audience.EDUCATIONAL_DEPUTY,
                priority=priority,
                generated_text="Review the documented signal and coordinate an appropriate support response.",
                reason_snapshot=snapshot,
            ),
        ]


RECOMMENDATION_RULES = (SignalSupportRule(),)
