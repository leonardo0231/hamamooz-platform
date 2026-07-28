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
