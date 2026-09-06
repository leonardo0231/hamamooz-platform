from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ColumnMatch:
    source: str
    canonical: str


ALIASES = {
    "national_code": {"کد ملی", "کدملی", "شماره ملی", "national code", "national_id"},
    "first_name": {"نام", "first name", "firstname"},
    "last_name": {"نام خانوادگی", "نام خانوادگي", "last name", "lastname"},
    "full_name": {"نام و نام خانوادگی", "نام کامل", "full name"},
    "class_code": {"کد کلاس", "class code"},
    "class_name": {"کلاس", "نام کلاس", "class", "class name"},
    "grade": {"پایه", "پایه تحصیلی", "grade"},
    "period": {"ماه", "دوره", "نوبت", "assessment period"},
}


def normalize_header(value: object) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"\s+", " ", text)
    return text


def map_columns(headers):
    result = {}
    normalized = {normalize_header(item): item for item in headers}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            key = normalize_header(alias)
            if key in normalized:
                result[canonical] = normalized[key]
                break
    return result


def discover_indicator_columns(headers):
    indicators = []
    for header in headers:
        value = str(header or "").strip()
        code = value.split("|", 1)[0].strip()
        if re.match(r"^[A-Z]{2,10}[_-]?\d+$", code, re.I):
            indicators.append(code.upper().replace("-", "_"))
    return indicators
