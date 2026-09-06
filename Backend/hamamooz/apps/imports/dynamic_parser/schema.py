from dataclasses import dataclass, field


@dataclass
class SheetSchema:
    name: str
    headers: list[str] = field(default_factory=list)
    rows_count: int = 0


@dataclass
class WorkbookSchema:
    sheets: list[SheetSchema] = field(default_factory=list)
    indicators: list[str] = field(default_factory=list)
    periods: list[str] = field(default_factory=list)

    def find_sheet(self, name: str):
        for sheet in self.sheets:
            if sheet.name == name:
                return sheet
        return None
