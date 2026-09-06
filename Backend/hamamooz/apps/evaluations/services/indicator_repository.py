from __future__ import annotations

from typing import Iterable


class IndicatorRepository:
    """Resolver layer for dynamically discovered indicators.

    Keeps import logic independent from fixed EDU_01..EDU_N assumptions.
    """

    def normalize_code(self, value: str) -> str:
        return value.strip().upper().replace(" ", "_")

    def resolve_discovered(self, codes: Iterable[str]) -> list[dict]:
        return [
            {
                "code": self.normalize_code(code),
            }
            for code in codes
            if code
        ]
