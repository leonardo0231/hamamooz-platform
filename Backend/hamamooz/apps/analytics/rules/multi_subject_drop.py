from collections import defaultdict

from hamamooz.apps.academics.models import SubjectResult

from .base import BaseRiskRule, SignalCandidate


class MultiSubjectDropRule(BaseRiskRule):
    code = "multi_subject_drop"
    version = 1
    default_parameters = {"minimum_drop": 2.0, "minimum_subjects": 2}

    def evaluate(self, enrollment, parameters):
        threshold = float(parameters.get("minimum_drop", self.default_parameters["minimum_drop"]))
        minimum_subjects = int(
            parameters.get("minimum_subjects", self.default_parameters["minimum_subjects"])
        )
        by_subject = defaultdict(list)
        for result in SubjectResult.objects.filter(
            enrollment__student_id=enrollment.student_id, average__isnull=False
        ).select_related("course_offering__grade_subject__subject", "course_offering__term"):
            by_subject[result.course_offering.grade_subject.subject.code].append(result)
        evidence = []
        for code, values in by_subject.items():
            values.sort(key=lambda item: item.course_offering.term.starts_on)
            if len(values) >= 2:
                drop = float(values[-2].average - values[-1].average)
                if drop >= threshold:
                    evidence.append({"subject": code, "drop": round(drop, 4)})
        if len(evidence) < minimum_subjects:
            return []
        return [
            SignalCandidate(
                severity="high",
                evidence={"affected_subjects": evidence, "count": len(evidence)},
                explanation=f"Performance dropped in {len(evidence)} subjects in the latest comparison.",
                window={
                    "comparison": "previous_subject_result",
                    "minimum_subjects": minimum_subjects,
                },
            )
        ]
