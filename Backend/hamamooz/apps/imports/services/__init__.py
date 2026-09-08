"""Compatibility exports for the historical import service module.

The project contains both ``imports/services.py`` and the newer
``imports/services/`` package.  Python resolves the package for
``hamamooz.apps.imports.services``; loading the legacy implementation here
keeps existing import jobs and tests working while new services can live in
this package.
"""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_LEGACY_MODULE_NAME = "hamamooz.apps.imports._legacy_services"
_LEGACY_PATH = Path(__file__).resolve().parent.parent / "services.py"
_SPEC = spec_from_file_location(_LEGACY_MODULE_NAME, _LEGACY_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - packaging failure
    raise ImportError("The legacy import service implementation is unavailable.")
_legacy = module_from_spec(_SPEC)
sys.modules[_LEGACY_MODULE_NAME] = _legacy
_SPEC.loader.exec_module(_legacy)
_ORIGINAL_LOAD_ROWS = _legacy._load_rows

# Keep the public surface of the old module available to callers that have not
# migrated to the package-level service modules yet.
for _name in dir(_legacy):
    if not _name.startswith("__") and _name not in {"_load_rows", "process_import_job"}:
        globals()[_name] = getattr(_legacy, _name)


def _load_rows(job):
    # Keep a stable reference to the legacy implementation.  The executor
    # temporarily replaces ``_legacy._load_rows`` so callers can monkeypatch
    # this package-level seam in tests without recursing into this wrapper.
    return _ORIGINAL_LOAD_ROWS(job)


def process_import_job(job_id):
    """Run the legacy executor while honoring package-level monkeypatches."""

    original_loader = _legacy._load_rows
    _legacy._load_rows = globals()["_load_rows"]
    try:
        return _legacy.process_import_job(job_id)
    finally:
        _legacy._load_rows = original_loader


__all__ = [name for name in globals() if not name.startswith("_")]
