from __future__ import annotations

import re


INDICATOR_PATTERN = re.compile(r"^(EDU|DEV|CHR|PER|SOC|SKL)_?\d+$", re.I)


def discover_indicator_codes(headers: list[str]) -> list[str]:
    """Discover assessment indicators without relying on fixed columns."""
    result = []
    for header in headers:
        value = str(header).strip().upper().replace("-", "_")
        if INDICATOR_PATTERN.match(value):
            result.append(value)
    return result
