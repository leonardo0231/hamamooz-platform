import json

from drf_spectacular.generators import SchemaGenerator


def _json_response_schema(operation, status_code):
    return operation["responses"][str(status_code)]["content"]["application/json"]["schema"]


def test_attendance_report_openapi_contract_is_complete():
    schema = SchemaGenerator().get_schema(request=None, public=True)
    paths = schema["paths"]

    student = paths["/api/v1/attendance-reports/student/"]["get"]
    assert {item["name"] for item in student["parameters"]} == {
        "date_from",
        "date_to",
        "enrollment",
        "scope",
    }
    assert _json_response_schema(student, 200) == {
        "$ref": "#/components/schemas/StudentAttendanceReportResponse"
    }

    classroom = paths["/api/v1/attendance-reports/class/"]["get"]
    assert {item["name"] for item in classroom["parameters"]} == {
        "academic_year",
        "class_section",
        "date_from",
        "date_to",
        "scope",
    }
    assert _json_response_schema(classroom, 200) == {
        "$ref": "#/components/schemas/ClassAttendanceReportResponse"
    }

    school = paths["/api/v1/attendance-reports/school/"]["get"]
    assert {item["name"] for item in school["parameters"]} == {
        "academic_year",
        "date_from",
        "date_to",
        "school",
        "scope",
    }
    assert _json_response_schema(school, 200) == {
        "$ref": "#/components/schemas/SchoolAttendanceReportResponse"
    }

    notify = paths["/api/v1/attendance-reports/notify-guardians/"]["post"]
    assert notify["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/NotifyGuardiansRequest"
    }
    assert _json_response_schema(notify, 201) == {
        "type": "array",
        "items": {"$ref": "#/components/schemas/ParentNotification"},
    }


def test_openapi_security_requirements_are_not_duplicated():
    schema = SchemaGenerator().get_schema(request=None, public=True)

    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            security = operation.get("security", [])
            normalized = [json.dumps(item, sort_keys=True) for item in security]
            assert len(normalized) == len(set(normalized)), (
                f"duplicate security for {method} {path}"
            )


def test_dashboard_and_attendance_policy_openapi_contracts_are_typed():
    schema = SchemaGenerator().get_schema(request=None, public=True)

    dashboard = schema["paths"]["/api/v1/dashboard/summary/"]["get"]
    assert _json_response_schema(dashboard, 200) == {
        "$ref": "#/components/schemas/DashboardSummary"
    }
    dashboard_schema = schema["components"]["schemas"]["DashboardSummary"]
    assert dashboard_schema["properties"]["counts"] == {
        "$ref": "#/components/schemas/DashboardCounts"
    }
    assert dashboard_schema["properties"]["latest_activities"]["type"] == "array"

    policy = schema["components"]["schemas"]["AttendancePolicyRequest"]
    channels = policy["properties"]["notification_channels"]
    assert channels["type"] == "array"
    assert channels["items"] == {"$ref": "#/components/schemas/NotificationChannelsEnum"}


def test_manual_evaluation_and_comprehensive_import_openapi_contracts_are_explicit():
    schema = SchemaGenerator().get_schema(request=None, public=True)
    paths = schema["paths"]

    catalog = paths["/api/v1/monthly-evaluations/catalog/"]["get"]
    assert _json_response_schema(catalog, 200) == {"$ref": "#/components/schemas/EvaluationCatalog"}

    manual = paths["/api/v1/monthly-evaluations/manual/"]["post"]
    assert manual["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ManualMonthlyEvaluationInputRequest"
    }
    assert _json_response_schema(manual, 200) == {
        "$ref": "#/components/schemas/ManualMonthlyEvaluationResponse"
    }
    assert _json_response_schema(manual, 201) == {
        "$ref": "#/components/schemas/ManualMonthlyEvaluationResponse"
    }

    manual_delete = paths["/api/v1/monthly-evaluations/{id}/manual/"]["delete"]
    assert manual_delete["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ManualEvaluationDeleteRequest"
    }
    assert "204" in manual_delete["responses"]

    import_create = paths["/api/v1/imports/"]["post"]
    create_schema = import_create["requestBody"]["content"]["multipart/form-data"]["schema"]
    assert create_schema == {"$ref": "#/components/schemas/ImportJobCreateRequest"}
    import_request = schema["components"]["schemas"]["ImportJobCreateRequest"]
    import_type = import_request["properties"]["import_type"]
    if "$ref" in import_type:
        enum_name = import_type["$ref"].rsplit("/", 1)[-1]
        import_type = schema["components"]["schemas"][enum_name]
    assert import_type["enum"] == ["comprehensive_school"]
