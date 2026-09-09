from dataclasses import dataclass, field


@dataclass
class ImportReport:
    file_name: str
    sheets: list[str] = field(default_factory=list)
    students_detected: int = 0
    indicators_detected: list[str] = field(default_factory=list)
    periods_detected: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self):
        return len(self.errors) == 0

    def add_warning(self, message):
        self.warnings.append(message)

    def add_error(self, message):
        self.errors.append(message)
