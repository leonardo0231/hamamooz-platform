from hamamooz.apps.reports.presentation import build_report_visuals


def test_visuals_are_derived_only_from_snapshot_data():
    report = {
        "summary": {"average": "18.50", "class_rank": 2, "status_label": "قبول"},
        "history": [
            {"label": "هفتم", "average": "16.25", "rank": 7},
            {"label": "هشتم", "average": "18.50", "rank": 2},
        ],
        "subjects": [
            {
                "title": "ریاضی",
                "average": "19.00",
                "continuous": "19",
                "final": "19",
                "passed": True,
            },
            {
                "title": "عربی",
                "average": "14.00",
                "continuous": "14",
                "final": "14",
                "passed": True,
            },
        ],
        "product_context": {
            "attendance": {
                "attendance_rate": 96,
                "finalized_session_count": 40,
                "unexcused_absence_count": 1,
            },
            "evaluations": [
                {
                    "metrics": [
                        {"code": "EDU_05", "title": "دقت و تمرکز", "value": 4},
                        {"code": "DEV_02", "title": "مسئولیت‌پذیری", "value": 5},
                        {"code": "PER_01", "title": "مدیریت زمان", "value": 4},
                    ]
                }
            ],
            "activities": [
                {"title": "پژوهش", "kind": "research", "result": "برگزیده"},
                {"title": "باشگاه کتاب", "kind": "cultural"},
            ],
        },
    }

    visuals = build_report_visuals(report)

    assert visuals["trend"]["has_data"] is True
    assert visuals["trend"]["points"][1]["value"] == "۱۸٫۵"
    assert visuals["attendance"]["rate"] == "۹۶"
    assert visuals["strengths"][0]["title"] == "ریاضی"
    assert visuals["improvements"][0]["title"] == "عربی"
    assert visuals["activities"][0]["icon"] == "research"
    assert [item["title"] for item in visuals["awards"]] == ["پژوهش"]


def test_missing_data_stays_explicitly_empty_instead_of_becoming_fake_values():
    visuals = build_report_visuals({"summary": {}, "subjects": [], "product_context": {}})

    assert visuals["trend"]["has_data"] is False
    assert visuals["radar"]["has_data"] is False
    assert visuals["attendance"]["has_data"] is False


def test_recommendation_override_does_not_fill_independent_family_support_area():
    visuals = build_report_visuals(
        {
            "summary": {},
            "subjects": [],
            "product_context": {
                "approved_recommendations": [
                    {"audience": "parent", "approved_text": "پیگیری هفتگی برنامهٔ مطالعه."}
                ]
            },
        },
        content_overrides={"recommendations": "متن نهاییِ تأییدشده برای خانواده."},
    )

    assert visuals["recommendations"][0] == "متن نهاییِ تأییدشده برای خانواده."
    assert visuals["support"] == []
    assert visuals["support_status"] == "missing"


def test_family_support_uses_only_explicit_support_notes():
    visuals = build_report_visuals(
        {
            "summary": {},
            "subjects": [],
            "product_context": {
                "approved_recommendations": [
                    {"audience": "parent", "approved_text": "توصیه آموزشی."}
                ],
                "support_notes": [{"text": "تماس با خانواده در هفته آینده."}],
            },
        }
    )

    assert visuals["recommendations"] == ["توصیه آموزشی."]
    assert visuals["support"] == ["تماس با خانواده در هفته آینده."]
    assert visuals["support_status"] == "available"


def test_all_available_evaluation_domains_are_retained_in_report_visuals():
    domains = [
        {"code": code, "title": title, "score": score, "completed_metrics": 1, "total_metrics": 2}
        for code, title, score in [
            ("EDU", "آموزشی", 18),
            ("DEV", "پرورشی", 16),
            ("CHR", "تربیتی", 15),
            ("DIS", "انضباطی", 14),
            ("CUL", "فرهنگی", 17),
            ("RES", "پژوهشی", 13),
            ("SPT", "ورزشی", 19),
            ("ART", "هنری", 12),
            ("PER", "مهارت‌های فردی", 16),
        ]
    ]

    visuals = build_report_visuals(
        {
            "summary": {"average": "18.00"},
            "subjects": [],
            "product_context": {"evaluation_analysis": {"domain_scores": domains}},
        }
    )

    assert [item["code"] for item in visuals["domains"]] == [item["code"] for item in domains]
    assert all(item["has_data"] for item in visuals["domains"])
    assert visuals["domains"][4]["value"] == 85
    assert visuals["radar"]["has_data"] is True
    assert len(visuals["radar"]["labels"]) == 9


def test_missing_evaluation_domains_are_canonical_and_not_zero():
    visuals = build_report_visuals(
        {
            "summary": {},
            "subjects": [],
            "product_context": {
                "evaluation_analysis": {
                    "domain_scores": [
                        {"code": "EDU", "title": "آموزشی", "score": 0},
                        {"code": "DIS", "title": "انضباطی", "score": None},
                    ]
                }
            },
        }
    )

    assert [item["code"] for item in visuals["domains"]] == [
        "EDU",
        "DEV",
        "CHR",
        "DIS",
        "CUL",
        "RES",
        "SPT",
        "ART",
        "PER",
    ]
    assert visuals["domains"][0]["value"] == 0
    assert visuals["domains"][0]["has_data"] is True
    assert visuals["domains"][3]["value"] is None
    assert visuals["domains"][3]["has_data"] is False
    assert visuals["radar"]["is_complete"] is False
    assert visuals["radar"]["labels"][3]["value"] == "ثبت نشده"
