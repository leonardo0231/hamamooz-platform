from collections import defaultdict
from math import ceil

from django.conf import settings
from django.db.models import Prefetch

from hamamooz.apps.students.models import Enrollment

from .catalog import DOMAIN_DEFINITIONS, METRIC_CATALOG
from .models import MonthlyEvaluation

PERFORMANCE_LEVELS = (
    (17, "عالی"),
    (14, "خوب"),
    (10, "متوسط"),
    (0, "ضعیف"),
)

DOMAIN_RECOMMENDATIONS = {
    "EDU": "برای حوزه آموزشی برنامه مطالعه هدفمند، تمرین تکمیلی و پیگیری تکالیف تنظیم شود.",
    "DEV": "برای حوزه پرورشی مسئولیت گروهی کوچک و تمرین مهارت‌های اجتماعی در نظر گرفته شود.",
    "CHR": "برای حوزه تربیتی اهداف کوتاه‌مدت همراه با بازخورد مثبت و پیگیری مشاور تعریف شود.",
    "DIS": "برای حوزه انضباطی علت بی‌نظمی بررسی و یک قرارداد رفتاری روشن با خانواده تنظیم شود.",
    "CUL": "برای حوزه فرهنگی فعالیت متناسب با علاقه دانش‌آموز و مشارکت هدایت‌شده پیشنهاد شود.",
    "RES": "برای حوزه پژوهشی یک پروژه کوچک با راهنمایی گام‌به‌گام و ارائه نتیجه تعریف شود.",
    "SPT": "برای حوزه ورزشی فعالیت بدنی متناسب و مشارکت در تمرین گروهی برنامه‌ریزی شود.",
    "ART": "برای حوزه هنری فرصت تولید و ارائه اثر متناسب با علاقه دانش‌آموز فراهم شود.",
    "PER": "برای مهارت‌های فردی برنامه هفتگی مدیریت زمان و تمرین حل تعارض اجرا شود.",
}

TREND_LABELS = {
    "improving": "پیشرفت",
    "stable": "ثبات",
    "declining": "افت",
    "insufficient_data": "داده ناکافی",
}


def _performance_level(score):
    if score is None:
        return None
    return next(label for minimum, label in PERFORMANCE_LEVELS if score >= minimum)


class EvaluationAnalyticsService:
    @staticmethod
    def evaluation_summary(evaluation: MonthlyEvaluation) -> dict:
        grouped = defaultdict(list)
        metric_scores = list(evaluation.metric_scores.all())
        for metric_score in metric_scores:
            definition = METRIC_CATALOG.get(metric_score.metric_code)
            if definition is not None:
                grouped[definition["domain_code"]].append(metric_score.value)

        domain_scores = []
        for code, (title, weight) in DOMAIN_DEFINITIONS.items():
            values = grouped[code]
            total_metrics = sum(
                definition["domain_code"] == code for definition in METRIC_CATALOG.values()
            )
            domain_scores.append(
                {
                    "code": code,
                    "title": title,
                    "weight": weight,
                    "score": round(sum(values) / len(values) * 4, 2) if values else None,
                    "completed_metrics": len(values),
                    "total_metrics": total_metrics,
                }
            )

        completed_metrics = sum(len(values) for values in grouped.values())
        completion_percent = round(completed_metrics / len(METRIC_CATALOG) * 100, 2)
        threshold_percent = max(
            1, min(100, getattr(settings, "EVALUATION_FINAL_COMPLETION_PERCENT", 100))
        )
        required_metrics = ceil(len(METRIC_CATALOG) * threshold_percent / 100)
        completion_status = "final" if completed_metrics >= required_metrics else "provisional"
        completed_domains = [item for item in domain_scores if item["score"] is not None]
        total_weight = sum(item["weight"] for item in completed_domains)
        overall_score = (
            round(
                sum(item["score"] * item["weight"] for item in completed_domains) / total_weight,
                2,
            )
            if total_weight
            else None
        )
        return {
            "domain_scores": domain_scores,
            "overall_score": overall_score,
            "completed_metrics": completed_metrics,
            "required_metrics": required_metrics,
            "completion_percent": completion_percent,
            "completion_status": completion_status,
            "performance_level": _performance_level(overall_score)
            if completion_status == "final"
            else None,
            "completion_warning": (
                None
                if completion_status == "final"
                else f"اطلاعات ناقص است؛ حداقل {required_metrics} شاخص باید تکمیل شود."
            ),
        }

    @classmethod
    def _evaluations_for(cls, enrollment):
        prefetched = getattr(enrollment, "_analytics_evaluations", None)
        if prefetched is not None:
            return sorted(prefetched, key=lambda item: item.month_no)
        return list(
            MonthlyEvaluation.objects.filter(enrollment=enrollment)
            .prefetch_related("metric_scores")
            .order_by("month_no")
        )

    @classmethod
    def _student_summary_without_rank(cls, enrollment) -> dict:
        evaluations = cls._evaluations_for(enrollment)
        monthly = []
        for evaluation in evaluations:
            summary = cls.evaluation_summary(evaluation)
            monthly.append(
                {
                    "month_no": evaluation.month_no,
                    "overall_score": summary["overall_score"],
                    "completion_percent": summary["completion_percent"],
                    "completion_status": summary["completion_status"],
                    "domain_scores": summary["domain_scores"],
                }
            )
        if not monthly:
            return {
                "enrollment": str(enrollment.id),
                "student": str(enrollment.student_id),
                "student_name": enrollment.student.full_name,
                "student_number": enrollment.student_number,
                "school": str(enrollment.school_id),
                "academic_year": str(enrollment.academic_year_id),
                "class_section": str(enrollment.class_section_id),
                "completion_status": "provisional",
                "completion_percent": 0.0,
                "overall_score": None,
                "performance_level": None,
                "first_month": None,
                "last_month": None,
                "change": None,
                "trend": "insufficient_data",
                "trend_label": TREND_LABELS["insufficient_data"],
                "strongest_domain": None,
                "weakest_domain": None,
                "recommendation": None,
                "completion_warning": "هنوز ارزیابی ماهانه‌ای ثبت نشده است.",
                "monthly_scores": [],
                "domain_scores": [],
            }

        current = monthly[-1]
        final_months = [item for item in monthly if item["completion_status"] == "final"]
        current_is_final = current["completion_status"] == "final"
        calculation_pool = final_months if current_is_final else monthly
        overall_values = [
            item["overall_score"] for item in calculation_pool if item["overall_score"] is not None
        ]
        overall_score = (
            round(sum(overall_values) / len(overall_values), 2) if overall_values else None
        )

        domain_scores = []
        for code, (title, _weight) in DOMAIN_DEFINITIONS.items():
            values = [
                domain["score"]
                for month in calculation_pool
                for domain in month["domain_scores"]
                if domain["code"] == code and domain["score"] is not None
            ]
            domain_scores.append(
                {"code": code, "title": title, "score": round(sum(values) / len(values), 2)}
                if values
                else {"code": code, "title": title, "score": None}
            )

        scored_domains = [item for item in domain_scores if item["score"] is not None]
        strongest = max(scored_domains, key=lambda item: item["score"]) if scored_domains else None
        weakest = min(scored_domains, key=lambda item: item["score"]) if scored_domains else None
        change = None
        trend = "insufficient_data"
        if current_is_final and len(final_months) >= 2:
            change = round(final_months[-1]["overall_score"] - final_months[0]["overall_score"], 2)
            epsilon = max(0, getattr(settings, "EVALUATION_TREND_EPSILON", 0.5))
            if change > epsilon:
                trend = "improving"
            elif change < -epsilon:
                trend = "declining"
            else:
                trend = "stable"

        recommendation = None
        if current_is_final and weakest:
            recommendation = DOMAIN_RECOMMENDATIONS[weakest["code"]]
            if trend == "declining":
                recommendation += " به دلیل روند افت، پیگیری با خانواده و مشاور در اولویت باشد."
            elif trend == "improving":
                recommendation += " روند مثبت با بازخورد و تشویق هدفمند تثبیت شود."

        return {
            "enrollment": str(enrollment.id),
            "student": str(enrollment.student_id),
            "student_name": enrollment.student.full_name,
            "student_number": enrollment.student_number,
            "school": str(enrollment.school_id),
            "academic_year": str(enrollment.academic_year_id),
            "class_section": str(enrollment.class_section_id),
            "completion_status": current["completion_status"],
            "completion_percent": current["completion_percent"],
            "overall_score": overall_score,
            "performance_level": _performance_level(overall_score) if current_is_final else None,
            "first_month": monthly[0]["month_no"],
            "last_month": monthly[-1]["month_no"],
            "change": change,
            "trend": trend,
            "trend_label": TREND_LABELS[trend],
            "strongest_domain": strongest if current_is_final else None,
            "weakest_domain": weakest if current_is_final else None,
            "recommendation": recommendation,
            "completion_warning": (
                None
                if current_is_final
                else "آخرین ارزیابی ناقص است؛ سطح، رتبه و پیشنهاد نهایی نمایش داده نمی‌شود."
            ),
            "monthly_scores": [
                {key: value for key, value in item.items() if key != "domain_scores"}
                for item in monthly
            ],
            "domain_scores": domain_scores,
        }

    @classmethod
    def student_summary(cls, enrollment, *, rank_scope="school") -> dict:
        if rank_scope not in {"school", "class"}:
            raise ValueError("rank_scope باید school یا class باشد.")
        summary = cls._student_summary_without_rank(enrollment)
        summary.update({"rank_scope": rank_scope, "rank": None, "ranked_count": 0})
        if summary["completion_status"] != "final" or summary["overall_score"] is None:
            return summary

        candidates = Enrollment.objects.filter(
            school=enrollment.school,
            academic_year=enrollment.academic_year,
            status=Enrollment.Status.ACTIVE,
        )
        if rank_scope == "class":
            candidates = candidates.filter(class_section=enrollment.class_section)
        evaluation_queryset = MonthlyEvaluation.objects.prefetch_related("metric_scores").order_by(
            "month_no"
        )
        candidates = candidates.select_related(
            "student", "school", "academic_year", "class_section"
        ).prefetch_related(
            Prefetch(
                "monthly_evaluations",
                queryset=evaluation_queryset,
                to_attr="_analytics_evaluations",
            )
        )
        ranked = []
        for candidate in candidates:
            candidate_summary = cls._student_summary_without_rank(candidate)
            if (
                candidate_summary["completion_status"] == "final"
                and candidate_summary["overall_score"] is not None
            ):
                ranked.append((candidate.id, candidate_summary["overall_score"]))
        ranked.sort(key=lambda item: (-item[1], str(item[0])))
        dense_rank = 0
        previous_score = None
        for candidate_id, score in ranked:
            if previous_score is None or score != previous_score:
                dense_rank += 1
            if candidate_id == enrollment.id:
                summary["rank"] = dense_rank
            previous_score = score
        summary["ranked_count"] = len(ranked)
        return summary

    @classmethod
    def cohort_summary(cls, enrollments, *, rank_scope="school") -> dict:
        enrollment_list = list(enrollments)
        students = [cls._student_summary_without_rank(item) for item in enrollment_list]
        ranked = sorted(
            [
                item
                for item in students
                if item["completion_status"] == "final" and item["overall_score"] is not None
            ],
            key=lambda item: (-item["overall_score"], item["student_name"], item["enrollment"]),
        )
        dense_rank = 0
        previous_score = None
        rank_by_enrollment = {}
        for item in ranked:
            if previous_score is None or item["overall_score"] != previous_score:
                dense_rank += 1
            rank_by_enrollment[item["enrollment"]] = dense_rank
            previous_score = item["overall_score"]
        for item in students:
            item["rank_scope"] = rank_scope
            item["rank"] = rank_by_enrollment.get(item["enrollment"])
            item["ranked_count"] = len(ranked)

        monthly_buckets = defaultdict(list)
        for item in students:
            for month in item["monthly_scores"]:
                if month["completion_status"] == "final" and month["overall_score"] is not None:
                    monthly_buckets[month["month_no"]].append(month["overall_score"])
        monthly_trend = [
            {
                "month_no": month_no,
                "average": round(sum(values) / len(values), 2),
                "students": len(values),
            }
            for month_no, values in sorted(monthly_buckets.items())
        ]

        domain_scores = []
        for code, (title, _weight) in DOMAIN_DEFINITIONS.items():
            values = [
                domain["score"]
                for item in students
                if item["completion_status"] == "final"
                for domain in item["domain_scores"]
                if domain["code"] == code and domain["score"] is not None
            ]
            domain_scores.append(
                {
                    "code": code,
                    "title": title,
                    "average": round(sum(values) / len(values), 2) if values else None,
                }
            )

        performance_distribution = {
            label: sum(item["performance_level"] == label for item in ranked)
            for _minimum, label in PERFORMANCE_LEVELS
        }
        evaluated = sum(bool(item["monthly_scores"]) for item in students)
        final_count = len(ranked)
        students.sort(
            key=lambda item: (
                item["rank"] is None,
                item["rank"] or 0,
                item["student_name"],
            )
        )
        return {
            "rank_scope": rank_scope,
            "counts": {
                "students": len(students),
                "evaluated": evaluated,
                "final": final_count,
                "provisional": evaluated - final_count,
                "ranked": len(ranked),
            },
            "monthly_trend": monthly_trend,
            "domain_scores": domain_scores,
            "performance_distribution": performance_distribution,
            "students": students,
        }
