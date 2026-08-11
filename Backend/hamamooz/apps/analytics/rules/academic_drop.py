from collections import defaultdict

from hamamooz.apps.academics.models import SubjectResult

from .base import BaseRiskRule, SignalCandidate


class AcademicDropRule(BaseRiskRule):
    code = "academic_drop"
    version = 1
    default_parameters = {"minimum_drop": 3.0}

    def evaluate(self, enrollment, parameters):
        by_subject = defaultdict(list)
        results = SubjectResult.objects.filter(
            enrollment__student_id=enrollment.student_id, average__isnull=False
        ).select_related("course_offering__grade_subject__subject", "course_offering__term")
        for result in results:
            by_subject[result.course_offering.grade_subject.subject].append(result)
        threshold = float(parameters.get("minimum_drop", self.default_parameters["minimum_drop"]))
        candidates = []
        for subject, values in by_subject.items():
            values.sort(key=lambda item: item.course_offering.term.starts_on)
            if len(values) < 2:
                continue
            previous, current = values[-2:]
            drop = float(previous.average - current.average)
            if drop >= threshold:
                candidates.append(
                    SignalCandidate(
                        severity="high" if drop >= threshold * 1.5 else "medium",
                        evidence={
                            "subject": subject.code,
                            "previous_average": float(previous.average),
                            "current_average": float(current.average),
                            "drop": round(drop, 4),
                        },
                        explanation=f"{subject.title} dropped by {drop:.2f} points compared with the previous term.",
                        window={"comparison": "previous_subject_result", "terms": 2},
                    )
                )
        # One active signal per deterministic rule keeps the signal lifecycle
        # unambiguous; the strongest subject is retained as exact evidence.
        return [max(candidates, key=lambda item: item.evidence["drop"])] if candidates else []
