"""The production report-PDF boundary.

Report archives must use the same fixed A3 landscape print contract as the
reviewed React report layout. Chromium is deliberately the only default
renderer; there is no implicit WeasyPrint fallback when the browser runtime is
missing.
"""

import base64
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings

from .chromium_renderer import ChromiumReportRenderer, ReportRendererUnavailable

__all__ = [
    "ChromiumReportRenderer",
    "ReportRendererUnavailable",
    "prepare_react_snapshot",
    "render_production_report_pdf",
]


def _inline_media_file_url(value: str) -> str:
    """Inline a confined local media file for the browser report entry.

    The snapshot builder turns local media paths into ``file://`` URLs for
    renderer safety. The React entry is normally loaded over HTTP, where a
    page is not allowed to request a local file. Inlining only files below
    Django's configured MEDIA_ROOT preserves the confinement check while
    making the authorized student photo/logo available to Chromium.
    """

    if not isinstance(value, str) or not value.startswith("file:"):
        return value
    parsed = urlparse(value)
    candidate = Path(unquote(parsed.path)).resolve()
    media_root = Path(settings.MEDIA_ROOT).resolve()
    if not candidate.is_relative_to(media_root) or not candidate.is_file():
        return ""
    content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(candidate.read_bytes()).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def prepare_react_snapshot(snapshot: dict) -> dict:
    """Prepare a frozen snapshot for injection into the React print entry."""

    from .services import _pdf_snapshot

    prepared = _pdf_snapshot(snapshot)
    for report in prepared.get("reports", []):
        for section, field in (("school", "logo_url"), ("student", "photo_url")):
            value = report.get(section, {}).get(field, "")
            report[section][field] = _inline_media_file_url(value)
    return prepared


def render_production_report_pdf(snapshot, *, renderer=None) -> bytes:
    """Render an approved snapshot through the Chromium production boundary.

    ``renderer`` is an explicit dependency-injection seam for deterministic
    unit tests and controlled service integrations.  Production callers leave
    it unset, which selects :class:`ChromiumReportRenderer`.  A missing
    Playwright package or browser bundle raises ``ReportRendererUnavailable``;
    it is intentionally not converted to a legacy engine fallback.
    """

    # Keep the legacy HTML call behind the explicit test/integration seam. It
    # is useful for renderer unit tests but is not the production report path.
    if renderer is not None:
        from .services import render_report_html

        html = render_report_html(prepare_react_snapshot(snapshot))
        pdf = renderer.render(
            html,
            base_url=f"{Path(settings.BASE_DIR).resolve().as_uri()}/",
        )
    else:
        frontend_url = str(getattr(settings, "REPORT_FRONTEND_URL", "") or "").strip()
        if not frontend_url:
            raise ReportRendererUnavailable(
                "Chromium React report rendering requires REPORT_FRONTEND_URL to point to "
                "the built report-sample.html entry."
            )
        active_renderer = ChromiumReportRenderer()
        pdf = active_renderer.render_snapshot(
            prepare_react_snapshot(snapshot),
            frontend_url=frontend_url,
            timeout_ms=int(getattr(settings, "REPORT_RENDER_TIMEOUT_MS", 30_000)),
        )
    if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF"):
        raise RuntimeError("The Chromium React report renderer returned invalid PDF bytes.")
    return pdf
