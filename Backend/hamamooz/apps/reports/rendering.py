"""The production report-PDF boundary.

Report archives must use the same fixed A3 landscape print contract as the
reviewed report layout.  Chromium is deliberately the only default renderer;
there is no implicit WeasyPrint fallback when the browser runtime is missing.
"""

from pathlib import Path

from django.conf import settings

from .chromium_renderer import ChromiumReportRenderer, ReportRendererUnavailable

__all__ = [
    "ChromiumReportRenderer",
    "ReportRendererUnavailable",
    "render_production_report_pdf",
]


def render_production_report_pdf(snapshot, *, renderer=None) -> bytes:
    """Render an approved snapshot through the Chromium production boundary.

    ``renderer`` is an explicit dependency-injection seam for deterministic
    unit tests and controlled service integrations.  Production callers leave
    it unset, which selects :class:`ChromiumReportRenderer`.  A missing
    Playwright package or browser bundle raises ``ReportRendererUnavailable``;
    it is intentionally not converted to a legacy engine fallback.
    """

    # Keep these imports local: services owns snapshot normalization and also
    # exposes this function for backwards-compatible callers.
    from .services import _pdf_snapshot, render_report_html

    html = render_report_html(_pdf_snapshot(snapshot))
    active_renderer = renderer or ChromiumReportRenderer()
    pdf = active_renderer.render(
        html,
        base_url=f"{Path(settings.BASE_DIR).resolve().as_uri()}/",
    )
    if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF"):
        raise RuntimeError("The Chromium report renderer returned invalid PDF bytes.")
    return pdf
