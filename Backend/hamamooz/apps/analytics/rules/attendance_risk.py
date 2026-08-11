from datetime import timedelta

from django.utils import timezone

from hamamooz.apps.attendance.models import AttendanceRecord, AttendanceSession

from .base import BaseRiskRule, SignalCandidate


class HighUnexcusedAbsenceRule(BaseRiskRule):
    code = "high_unexcused_absence"
    version = 1
    default_parameters = {"window_days": 30, "minimum_count": 3}

    def evaluate(self, enrollment, parameters):
        days = int(parameters.get("window_days", self.default_parameters["window_days"]))
        minimum = int(parameters.get("minimum_count", self.default_parameters["minimum_count"]))
        start = timezone.localdate() - timedelta(days=days)
        count = AttendanceRecord.objects.filter(
            enrollment=enrollment,
            status=AttendanceRecord.Status.ABSENT_UNEXCUSED,
            session__status=AttendanceSession.Status.FINALIZED,
            session__session_date__gte=start,
        ).count()
        if count < minimum:
            return []
        return [
            SignalCandidate(
                severity="critical" if count >= minimum * 2 else "high",
                evidence={"unexcused_absence_count": count},
                explanation=f"{count} finalized unexcused absences were recorded in the recent window.",
                window={"days": days, "start": start.isoformat()},
            )
        ]
