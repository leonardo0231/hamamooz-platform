from dataclasses import dataclass


@dataclass(frozen=True)
class SignalCandidate:
    severity: str
    evidence: dict
    explanation: str
    window: dict


class BaseRiskRule:
    code = "base"
    version = 1
    default_parameters = {}

    def evaluate(self, enrollment, parameters):  # pragma: no cover - interface
        raise NotImplementedError
