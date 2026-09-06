"""
Compatibility adapter between legacy monthly evaluation data and the new
period/indicator based assessment architecture.

This layer intentionally keeps legacy models untouched while allowing new
imports and reports to use the generic assessment model.
"""


def build_assessment_payload(*, student, period, indicator, score, recorded_by=None):
    return {
        "student": student,
        "period": period,
        "indicator": indicator,
        "score": score,
        "recorded_by": recorded_by,
    }


def legacy_month_to_period_title(month_no):
    """Create a safe title for migrating old month based records."""
    return f"ماه {month_no}"
