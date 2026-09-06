"""Compatibility exports for evaluations service modules.

The project contains both a legacy services.py module and a services package.
Python resolves the package first, so public imports like
``from .services import EvaluationAnalyticsService`` need this bridge.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


_legacy_services_path = Path(__file__).resolve().parent.parent / "services.py"
_legacy_spec = spec_from_file_location(
    "hamamooz.apps.evaluations._legacy_services",
    _legacy_services_path,
)

if _legacy_spec and _legacy_spec.loader:
    _legacy_module = module_from_spec(_legacy_spec)
    sys.modules[_legacy_spec.name] = _legacy_module
    _legacy_spec.loader.exec_module(_legacy_module)
    EvaluationAnalyticsService = _legacy_module.EvaluationAnalyticsService
else:
    raise ImportError("Unable to load legacy evaluations services module")

__all__ = ["EvaluationAnalyticsService"]
