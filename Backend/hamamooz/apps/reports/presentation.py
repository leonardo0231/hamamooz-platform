"""Pure, print-safe view data for the analytical report template.

The report snapshot deliberately stores source facts, rather than HTML or CSS.
This module derives only deterministic visual coordinates and formatted values
from that frozen data just before rendering.  It keeps browser chart code in the
browser print path while preserving the same analysis model in the PDF.
"""

from __future__ import annotations

from math import cos, isfinite, pi, sin
from typing import Any

from hamamooz.apps.evaluations.catalog import DOMAIN_DEFINITIONS

PERSIAN_DIGITS = str.maketrans("0123456789.-", "۰۱۲۳۴۵۶۷۸۹٫-")

METRIC_TITLES = {
    "EDU_01": "نمرات درسی",
    "EDU_02": "پیشرفت نسبت به قبل",
    "EDU_03": "انجام تکالیف",
    "EDU_04": "مشارکت در کلاس",
    "EDU_05": "دقت و تمرکز",
    "DEV_01": "احترام و همکاری",
    "DEV_02": "مسئولیت‌پذیری",
    "DEV_04": "نظم شخصی",
    "DEV_10": "اعتماد به نفس",
    "CHR_01": "خودکنترلی",
    "CHR_02": "انگیزه برای یادگیری",
    "CHR_03": "پشتکار",
    "CHR_08": "مدیریت استرس",
    "DIS_01": "حضور و غیاب",
    "DIS_03": "رعایت قوانین",
    "PER_01": "مدیریت زمان",
    "PER_02": "مهارت ارتباطی",
    "PER_04": "کار تیمی",
    "PER_05": "تفکر انتقادی",
}


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _fa(value: float | None, places: int = 0) -> str:
    if value is None:
        return "—"
    rendered = f"{value:.{places}f}"
    if places:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered.translate(PERSIAN_DIGITS)


def _percent(value: float | None, maximum: float = 100) -> int | None:
    if value is None:
        return None
    return int(max(0, min(maximum, round(value))))


def _metric_items(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the latest monthly metric values, normalised to percentages."""
    evaluations = context.get("evaluations") or []
    if not evaluations:
        return []
    latest = evaluations[-1]
    entries = latest.get("metrics") or []
    if not entries:
        entries = [
            {"code": code, "title": METRIC_TITLES.get(code, code), "value": value}
            for code, value in (latest.get("metric_scores") or {}).items()
        ]
    normalized = []
    for item in entries:
        raw = _number(item.get("value"))
        if raw is None:
            continue
        normalized.append(
            {
                "code": item.get("code") or item.get("metric_code") or "",
                "title": item.get("title") or METRIC_TITLES.get(item.get("code"), item.get("code")),
                "value": max(0, min(100, raw * 20)),
            }
        )
    return normalized


def _domain_items(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the canonical nine-domain analysis in report-friendly units.

    ``EvaluationAnalyticsService`` stores domain scores on a 0–20 scale while
    the report visuals use percentages.  Preserve both values and retain
    domains with no score so the report can distinguish "not assessed" from a
    zero result.  A metric-only fallback keeps old frozen snapshots readable.
    """
    analysis = context.get("evaluation_analysis") or context.get("analysis") or {}
    rows = analysis.get("domain_scores") or []
    if not rows:
        # Older snapshots do not have the service result.  Group the latest
        # metric values by their persisted domain metadata where available.
        latest = (context.get("evaluations") or [])[-1:]
        grouped: dict[str, list[float]] = {}
        titles: dict[str, str] = {}
        for evaluation in latest:
            metrics = evaluation.get("metrics") or []
            for metric in metrics:
                code = str(metric.get("domain_code") or metric.get("code") or "")
                domain_code = code.split("_", 1)[0]
                if not domain_code:
                    continue
                raw = _number(metric.get("value"))
                if raw is None:
                    continue
                grouped.setdefault(domain_code, []).append(raw * 4)
                titles.setdefault(domain_code, metric.get("domain_title") or domain_code)
        rows = [
            {"code": code, "title": titles[code], "score": sum(values) / len(values)}
            for code, values in grouped.items()
        ]
    # A report must expose a stable nine-domain contract even when a workbook
    # contains only a subset of the indicators.  The old implementation
    # returned only rows present in the snapshot, which made the same student
    # appear to have a different set of analyses from month to month.
    rows_by_code = {
        str(item.get("code")): item
        for item in rows
        if isinstance(item, dict) and str(item.get("code") or "") in DOMAIN_DEFINITIONS
    }
    domains = []
    for code, (canonical_title, weight) in DOMAIN_DEFINITIONS.items():
        item = rows_by_code.get(code, {})
        raw_score = _number(item.get("score"))
        score = raw_score if raw_score is not None and 0 <= raw_score <= 20 else None
        # The analytics service stores a 0–20 score.  ``value`` is accepted as
        # an explicit percentage only for old frozen integrations; it is never
        # synthesized when both source values are absent or null.
        raw_value = _number(item.get("value"))
        value = score * 5 if score is not None else raw_value
        if value is not None:
            value = max(0, min(100, value))
        domains.append(
            {
                "code": code,
                "title": item.get("title") or item.get("domain_title") or canonical_title,
                "score": score,
                "value": value,
                "percent": _percent(value) if value is not None else None,
                "weight": item.get("weight", weight),
                "completed_metrics": item.get("completed_metrics", 0),
                "total_metrics": item.get("total_metrics", 0),
                "has_data": value is not None,
            }
        )
    return domains


def _trend(history: list[dict[str, Any]]) -> dict[str, Any]:
    points = []
    valid = [item for item in history if _number(item.get("average")) is not None]
    if not valid:
        return {
            "has_data": False,
            "points": [],
            "guides": [],
            "rank_path": "",
            "rank_points": [],
            "growth_path": "",
            "growth_points": [],
        }
    count = len(valid)
    for index, item in enumerate(valid):
        value = _number(item.get("average")) or 0
        x = 30 + (300 * index / max(1, count - 1))
        y = 116 - ((max(10, min(20, value)) - 10) / 10 * 86)
        points.append(
            {
                "x": f"{x:.1f}",
                "y": f"{y:.1f}",
                "label_y": f"{y - 9:.1f}",
                "label": item.get("label", "—"),
                "value": _fa(value, 2),
                "rank": _fa(_number(item.get("rank"))) if item.get("rank") else "",
            }
        )
    path = " ".join(f"{item['x']},{item['y']}" for item in points)

    def relative_points(values: list[tuple[dict[str, str], float]], *, inverse: bool = False):
        """Project a real secondary series onto the same compact SVG canvas.

        Rank and percentage growth do not share the average's 10–20 scale.  A
        local normalisation keeps them readable while their labels remain
        explicit in the legend; we never manufacture a series when its source
        data is missing.
        """

        if len(values) < 2:
            return []
        low = min(value for _, value in values)
        high = max(value for _, value in values)
        span = high - low
        projected = []
        for point, value in values:
            ratio = 0.5 if span == 0 else (value - low) / span
            if inverse:
                ratio = 1 - ratio
            y = 111 - ratio * 72
            projected.append(
                {
                    "x": point["x"],
                    "y": f"{y:.1f}",
                    "value": _fa(value, 1),
                }
            )
        return projected

    rank_values = [
        (point, rank)
        for item, point in zip(valid, points, strict=True)
        if (rank := _number(item.get("rank"))) is not None
    ]
    rank_points = relative_points(rank_values, inverse=True)
    growth_values = []
    previous = None
    for item, point in zip(valid, points, strict=True):
        average = _number(item.get("average"))
        if average is not None and previous not in (None, 0):
            growth_values.append((point, ((average - previous) / previous) * 100))
        if average is not None:
            previous = average
    growth_points = relative_points(growth_values)
    return {
        "has_data": True,
        "points": points,
        "path": path,
        "area_path": f"30,116 {path} 330,116",
        "rank_path": " ".join(f"{item['x']},{item['y']}" for item in rank_points),
        "rank_points": rank_points,
        "growth_path": " ".join(f"{item['x']},{item['y']}" for item in growth_points),
        "growth_points": growth_points,
        "guides": [
            {"value": _fa(float(value), 0), "y": f"{116 - ((value - 10) / 10 * 86):.1f}"}
            for value in (10, 12.5, 15, 17.5, 20)
        ],
    }


def _radar(items: list[dict[str, Any]]) -> dict[str, Any]:
    if len(items) < 3:
        return {
            "has_data": False,
            "is_complete": False,
            "available_count": 0,
            "labels": [],
            "outline": "",
            "value_points": "",
            "grids": [],
        }
    center = 60
    radius = 42
    count = len(items)

    def point(index: int, size: float) -> tuple[float, float]:
        angle = -pi / 2 + 2 * pi * index / count
        return center + cos(angle) * size, center + sin(angle) * size

    labels = []
    values = []
    available_values = []
    outline = []
    for index, item in enumerate(items):
        x, y = point(index, radius)
        label_x, label_y = point(index, radius + 12)
        value = _number(item.get("value"))
        value_x, value_y = point(index, radius * (value or 0) / 100)
        outline.append(f"{x:.1f},{y:.1f}")
        values.append(f"{value_x:.1f},{value_y:.1f}")
        if value is not None:
            available_values.append(value)
        labels.append(
            {
                "x": f"{label_x:.1f}",
                "y": f"{label_y:.1f}",
                "title": item["title"],
                # Keep the numeric key beside every axis label so the printed
                # chart remains interpretable without colour or hover state.
                "value": _fa(value, 0) if value is not None else "ثبت نشده",
                "value_raw": value,
                "has_data": value is not None,
            }
        )
    grids = []
    for scale in (0.25, 0.5, 0.75, 1):
        grids.append(
            " ".join(
                f"{x:.1f},{y:.1f}"
                for x, y in (point(index, radius * scale) for index in range(count))
            )
        )
    return {
        "has_data": bool(available_values),
        "is_complete": len(available_values) == len(items),
        "available_count": len(available_values),
        "labels": labels,
        "outline": " ".join(outline),
        # A filled polygon with missing vertices visually turns null into a
        # zero.  Keep the geometry available for clients that can render
        # gaps, but leave the print polygon empty unless every domain has a
        # measured value.
        "value_points": " ".join(values) if len(available_values) == len(items) else "",
        "grids": grids,
    }


def _bars(
    items: list[dict[str, Any]], *, limit: int = 6, inverse: bool = False
) -> list[dict[str, Any]]:
    valid = [item for item in items if item.get("value") is not None]
    sorted_items = sorted(valid, key=lambda item: item["value"], reverse=not inverse)[:limit]
    return [
        {
            "title": item["title"],
            "percent": _percent(item["value"]),
            "value": _fa(item["value"], 0),
        }
        for item in sorted_items
    ]


def build_report_visuals(
    report: dict[str, Any], *, content_overrides: dict[str, str] | None = None
) -> dict[str, Any]:
    """Build a compact visual view model from a frozen report snapshot.

    Draft-level copy is intentionally accepted only as plain, already-validated
    text.  It is folded into view data here rather than being interpolated as
    template source, so the immutable PDF stays safe and the approved override
    is visible in its intended recommendation areas.
    """
    context = report.get("product_context") or {}
    overrides = content_overrides if isinstance(content_overrides, dict) else {}
    subjects = []
    for row in report.get("subjects") or []:
        average = _number(row.get("average"))
        subjects.append(
            {
                "title": row.get("title", "—"),
                "continuous": row.get("continuous") or "—",
                "midterm": row.get("midterm") or "—",
                "final": row.get("final") or "—",
                "average": average,
                "average_display": _fa(average, 2),
                "passed": bool(row.get("passed")),
            }
        )

    attendance = context.get("attendance") or {}
    attendance_rate = _number(attendance.get("attendance_rate"))
    metrics = _metric_items(context)
    domains = _domain_items(context)
    metric_map = {item["code"]: item for item in metrics}
    behavior = [item for item in metrics if item["code"].startswith(("DEV_", "CHR_", "DIS_"))][:10]
    academic = [item for item in metrics if item["code"].startswith(("EDU_", "PER_"))][:6]

    # Prefer the canonical nine domains when available.  This makes the radar
    # and its companion list reflect exactly what the analysis service knows,
    # instead of silently dropping cultural, research, sport and arts data.
    # Keep all canonical axes in the radar, including unassessed domains.  A
    # missing axis is labelled explicitly instead of being removed or treated
    # as a score of zero.
    radar_items = [{"title": item["title"], "value": item["value"]} for item in domains]
    if not domains:
        radar_items = []
        academic_average = _number(report.get("summary", {}).get("average"))
        if academic_average is not None:
            radar_items.append({"title": "آموزشی", "value": academic_average * 5})
        if attendance_rate is not None:
            radar_items.append({"title": "حضور", "value": attendance_rate})
        for code, title in (
            ("DEV_02", "مسئولیت"),
            ("EDU_05", "تمرکز"),
            ("DEV_01", "همکاری"),
            ("PER_01", "مدیریت زمان"),
        ):
            if code in metric_map:
                radar_items.append({"title": title, "value": metric_map[code]["value"]})
        radar_items = radar_items[:6]
    academic_average = _number(report.get("summary", {}).get("average"))

    readiness = academic or [
        {"title": item["title"], "value": item["average"] * 5}
        for item in subjects
        if item["average"] is not None
    ]
    activity_icons = {
        # Keep the snapshot semantic and font-independent.  The HTML
        # presenter maps these names to local SVG sticker artwork so a PDF
        # never depends on an emoji glyph installed on the host machine.
        "sport": "sport",
        "research": "research",
        "competition": "competition",
        "cultural": "cultural",
        "art": "art",
    }
    activity_badges = {
        "sport": "SPORT",
        "research": "EDU",
        "competition": "AWARD",
        "cultural": "CULT",
        "art": "ART",
    }
    activities = [
        {
            "icon": activity_icons.get(item.get("kind"), "school"),
            "kind": item.get("kind") or "school",
            "badge": activity_badges.get(item.get("kind"), "ACT"),
            "title": item.get("title", "فعالیت مدرسه"),
            "text": item.get("result")
            or (
                f"رتبه {_fa(_number(item.get('placement')))}" if item.get("placement") else "ثبت‌شده"
            ),
        }
        for item in (context.get("activities") or [])[:7]
    ]
    all_recommendations = [
        item
        for item in (context.get("approved_recommendations") or [])
        if item.get("approved_text")
    ]
    recommendations = [
        item.get("approved_text")
        for item in all_recommendations
        if item.get("audience") in (None, "parent", "student")
    ]
    teacher_recommendations = [
        item.get("approved_text")
        for item in all_recommendations
        if item.get("audience") in ("teacher", "guide_teacher", "educational_deputy")
    ]
    follow_ups = [
        item.get("explanation")
        for item in (context.get("analytics_signals") or [])
        if item.get("explanation")
    ]
    behavior_events = context.get("behavior_events") or []
    skills21 = [
        {
            "title": item["title"],
            "stars": max(0, min(5, round(item["value"] / 20))),
            "value": _fa(item["value"], 0),
        }
        for item in metrics
        if item["code"].startswith(("PER_", "DEV_", "CHR_"))
    ][:9]
    counselor = [
        item if isinstance(item, str) else item.get("explanation")
        for item in (context.get("counselor_report") or context.get("analytics_signals") or [])
    ]
    counselor = [item for item in counselor if item][:8]
    support = [
        item if isinstance(item, str) else item.get("text")
        for item in (context.get("support_notes") or [])
    ]
    support = [item for item in support if item][:3]
    recommendation_override = overrides.get("recommendations")
    if isinstance(recommendation_override, str) and recommendation_override.strip():
        recommendations = [recommendation_override.strip(), *recommendations]
    # Family support is an independent source.  Approved recommendations are
    # intentionally not copied into this panel: an instructional recommendation
    # is not evidence that the family-support team has recorded a plan.
    awards = [item for item in activities if item.get("text") and item.get("text") != "ثبت‌شده"][:5]

    return {
        "trend": _trend(report.get("history") or []),
        "radar": _radar(radar_items),
        "domains": domains,
        "domain_scores": domains,
        "subjects": subjects,
        "strengths": _bars(
            [
                {"title": item["title"], "value": item["average"] * 5}
                for item in subjects
                if item["average"] is not None
            ]
        ),
        "improvements": _bars(
            [
                {"title": item["title"], "value": item["average"] * 5}
                for item in subjects
                if item["average"] is not None
            ],
            inverse=True,
        ),
        "behavior": [
            {
                "title": item["title"],
                "stars": max(0, min(5, round(item["value"] / 20))),
                "value": _fa(item["value"], 0),
            }
            for item in behavior[:10]
        ],
        "readiness": _bars(readiness),
        "activities": activities,
        "awards": awards,
        "skills21": skills21,
        "counselor": counselor,
        "teacher_recommendations": teacher_recommendations,
        "support": support,
        "support_status": "available" if support else "missing",
        "recommendations": recommendations[:4],
        "follow_ups": follow_ups,
        "attendance": {
            "has_data": attendance_rate is not None,
            "rate": _fa(attendance_rate, 0),
            "sessions": _fa(_number(attendance.get("finalized_session_count"))),
            "unexcused": _fa(_number(attendance.get("unexcused_absence_count"))),
            "late": _fa(_number(attendance.get("late_count"))),
        },
        "summary": {
            "average": _fa(academic_average, 2),
            "rank": _fa(_number(report.get("summary", {}).get("class_rank"))),
            "status": report.get("summary", {}).get("status_label", "—"),
            "behavior_positive": _fa(
                float(sum(item.get("polarity") == "positive" for item in behavior_events))
            ),
            "behavior_follow_up": _fa(
                float(sum(item.get("polarity") == "negative" for item in behavior_events))
            ),
        },
    }
