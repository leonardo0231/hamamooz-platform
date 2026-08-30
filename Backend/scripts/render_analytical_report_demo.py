"""Render the same A3 analytical template used by the reporting service.

This script contains fictional data only.  It is intentionally useful for
stakeholder demonstrations and visual regression checks without a production
database or a real student's information.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django

django.setup()

from hamamooz.apps.reports.services import render_report_pdf  # noqa: E402


def sample_snapshot() -> dict:
    return {
        "template": {
            "blocks": [
                "student_identity",
                "academic_summary",
                "attendance_summary",
                "evaluation_radar",
                "strengths",
                "weaknesses",
                "recommendations",
                "signatures",
            ],
            "presentation": {"page_size": "a3_landscape"},
        },
        "reports": [
            {
                "demo": True,
                "organization": {"name": "سامانه هوشمند هم‌آموز"},
                "school": {"name": "دبیرستان پسرانه دورهٔ اول آینده", "branch": "شعبه مرکزی", "address": "تهران، منطقهٔ آموزشی نمونه", "phone": "۰۲۱-۸۸۸۸۸۸۸۸", "manager": "مدیر مدرسه", "logo_url": ""},
                "student": {"full_name": "آرین محمدی", "national_id": "۰۰۱۲۳۴۵۶۷۸", "student_number": "۹۹-۲۰۲۴", "photo_url": ""},
                "academic": {"year": "۱۴۰۴–۱۴۰۵", "term": "نوبت اول", "grade": "پایه نهم", "class": "نهم / الف"},
                "summary": {"average": "18.78", "class_rank": 3, "passed": True, "status_label": "قبول", "formula_version": "standard-v1"},
                "history": [
                    {"label": "پایه هفتم", "year": "۱۴۰۲–۱۴۰۳", "average": "16.20", "rank": 12},
                    {"label": "پایه هشتم", "year": "۱۴۰۳–۱۴۰۴", "average": "17.45", "rank": 7},
                    {"label": "پایه نهم", "year": "۱۴۰۴–۱۴۰۵", "average": "18.78", "rank": 3},
                ],
                "subjects": [
                    {"title": "ریاضی", "coefficient": "2", "continuous": "19.50", "midterm": "19.00", "final": "19.50", "average": "19.50", "passed": True},
                    {"title": "علوم تجربی", "coefficient": "2", "continuous": "18.50", "midterm": "18.75", "final": "19.20", "average": "18.90", "passed": True},
                    {"title": "فارسی", "coefficient": "2", "continuous": "18.00", "midterm": "18.00", "final": "18.80", "average": "18.40", "passed": True},
                    {"title": "مطالعات اجتماعی", "coefficient": "2", "continuous": "18.00", "midterm": "17.50", "final": "18.40", "average": "18.10", "passed": True},
                    {"title": "عربی", "coefficient": "1", "continuous": "17.00", "midterm": "17.00", "final": "17.60", "average": "17.20", "passed": True},
                    {"title": "زبان انگلیسی", "coefficient": "2", "continuous": "19.00", "midterm": "19.00", "final": "19.50", "average": "19.20", "passed": True},
                    {"title": "پیام‌های آسمانی", "coefficient": "1", "continuous": "18.50", "midterm": "18.00", "final": "18.50", "average": "18.30", "passed": True},
                ],
                "product_context": {
                    "attendance": {"finalized_session_count": 42, "record_count": 42, "present_count": 40, "unexcused_absence_count": 1, "excused_absence_count": 1, "late_count": 2, "attendance_rate": 95.2},
                    "evaluations": [{"month_no": 8, "framework_version": "1.0", "metrics": [
                        {"code": "EDU_01", "title": "نمرات درسی", "value": 5}, {"code": "EDU_02", "title": "پیشرفت نسبت به قبل", "value": 4},
                        {"code": "EDU_05", "title": "دقت و تمرکز", "value": 4}, {"code": "DEV_01", "title": "احترام و همکاری", "value": 5},
                        {"code": "DEV_02", "title": "مسئولیت‌پذیری", "value": 5}, {"code": "DEV_04", "title": "نظم شخصی", "value": 4},
                        {"code": "CHR_02", "title": "انگیزه برای یادگیری", "value": 4}, {"code": "CHR_03", "title": "پشتکار", "value": 4},
                        {"code": "PER_01", "title": "مدیریت زمان", "value": 4}, {"code": "PER_02", "title": "مهارت ارتباطی", "value": 4},
                    ]}],
                    "behavior_events": [{"polarity": "positive"}, {"polarity": "positive"}],
                    "activities": [
                        {"title": "المپیاد علمی", "kind": "competition", "result": "مقام دوم منطقه", "placement": 2},
                        {"title": "مسابقات ورزشی", "kind": "sport", "result": "عضو تیم مدرسه", "placement": None},
                        {"title": "پژوهش و تحلیل", "kind": "research", "result": "پروژه برگزیده", "placement": 1},
                        {"title": "باشگاه کتاب‌خوانی", "kind": "cultural", "result": "مشارکت مستمر", "placement": None},
                    ],
                    "analytics_signals": [
                        {"explanation": "برنامهٔ مطالعهٔ روزانه و پیگیری تکالیف، روند رشد را در سه پایه پایدار کرده است."},
                        {"explanation": "تقویت نقش ارائه‌دهنده در فعالیت‌های گروهی، مهارت ارتباطی دانش‌آموز را پررنگ‌تر می‌کند."},
                        {"explanation": "زمان‌بندی مرور پیش از آزمون، فرصت بهبود بیشتر در درس عربی را فراهم می‌کند."},
                    ],
                    "approved_recommendations": [
                        {"approved_text": "برنامهٔ ثابت مطالعهٔ روزانه را برای تثبیت رشد تحصیلی ادامه دهد."},
                        {"approved_text": "در پروژه‌های پژوهشی و کارگروهی، مسئولیت ارائهٔ نهایی را تجربه کند."},
                        {"approved_text": "مرور کوتاه و منظم درس عربی در برنامهٔ هفتگی قرار گیرد."},
                    ],
                },
            }
        ],
    }


def main() -> None:
    output = WORKSPACE_ROOT / "output" / "pdf" / "hamamooz-analytical-report-sample-fa.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(render_report_pdf(sample_snapshot()))
    print(output)


if __name__ == "__main__":
    main()
