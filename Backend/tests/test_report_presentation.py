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
    assert visuals["activities"][0]["icon"] == "🔬"
    assert [item["title"] for item in visuals["awards"]] == ["پژوهش"]


def test_missing_data_stays_explicitly_empty_instead_of_becoming_fake_values():
    visuals = build_report_visuals({"summary": {}, "subjects": [], "product_context": {}})

    assert visuals["trend"]["has_data"] is False
    assert visuals["radar"]["has_data"] is False
    assert visuals["attendance"]["has_data"] is False


def test_approved_parent_copy_is_visible_in_both_recommendation_areas():
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
    assert visuals["support"][0] == "متن نهاییِ تأییدشده برای خانواده."
