from dataclasses import dataclass, field


@dataclass
class ValidationIssue:
    level: str
    message: str
    row: int | None = None
    column: str | None = None


@dataclass
class ValidationResult:
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def warnings(self):
        return [i for i in self.issues if i.level == "warning"]

    @property
    def errors(self):
        return [i for i in self.issues if i.level == "error"]


class DynamicImportValidator:
    """Validation layer independent from a specific Excel template."""

    REQUIRED_FIELDS = {
        "students": {"national_code"},
        "assessments": {"national_code"},
    }

    def validate_headers(self, mapped_headers, import_type="students"):
        issues = []
        required = self.REQUIRED_FIELDS.get(import_type, set())
        missing = required - set(mapped_headers)
        for field in sorted(missing):
            issues.append(
                ValidationIssue(
                    level="error",
                    message=f"Required field missing: {field}",
                    column=field,
                )
            )
        return ValidationResult(valid=not issues, issues=issues)

    def validate_rows(self, rows):
        issues = []
        for index, row in enumerate(rows, start=2):
            if not any(value not in (None, "") for value in row.values()):
                issues.append(
                    ValidationIssue(
                        level="warning",
                        message="Empty row skipped",
                        row=index,
                    )
                )
        return ValidationResult(valid=not any(i.level == "error" for i in issues), issues=issues)
