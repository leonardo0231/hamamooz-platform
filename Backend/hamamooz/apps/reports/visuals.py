from statistics import mean


def build_growth_chart(history):
    """Prepare growth chart data from assessment history."""
    return {
        "type": "line",
        "labels": [item.get("year") for item in history],
        "datasets": [
            {
                "label": "Average",
                "data": [item.get("average") for item in history],
            }
        ],
    }


def build_indicator_comparison(subjects):
    """Prepare comparison chart payload for indicators/subjects."""
    return {
        "type": "bar",
        "labels": [item.get("title") for item in subjects],
        "datasets": [
            {
                "label": "Score",
                "data": [item.get("average") for item in subjects],
            }
        ],
    }


def build_report_visuals(report, content_overrides=None):
    history = report.get("history", [])
    subjects = report.get("subjects", [])
    return {
        "growth": build_growth_chart(history),
        "comparison": build_indicator_comparison(subjects),
        "overall_average": report.get("summary", {}).get("average"),
        "subject_count": len(subjects),
    }
