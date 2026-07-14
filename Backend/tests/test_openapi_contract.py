from pathlib import Path

import pytest
from django.conf import settings
from drf_spectacular.generators import (
    SchemaGenerator,
)


REQUIRED_PATHS = {
    "/api/v1/auth/login/",
    "/api/v1/auth/refresh/",
    "/api/v1/auth/me/",
    "/api/v1/organizations/",
    "/api/v1/schools/",
    "/api/v1/memberships/",
}


@pytest.mark.django_db
def test_runtime_schema_contains_required_paths() -> None:
    schema = SchemaGenerator().get_schema(
        request=None,
        public=True,
    )

    assert schema is not None

    paths = set(schema["paths"])

    assert REQUIRED_PATHS <= paths


def test_committed_schema_contains_required_paths() -> None:
    schema_path = (
        Path(settings.BASE_DIR)
        / "docs"
        / "openapi-schema.yml"
    )

    content = schema_path.read_text(
        encoding="utf-8"
    )

    for path in REQUIRED_PATHS:
        assert f"  {path}:" in content