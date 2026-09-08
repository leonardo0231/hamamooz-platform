from .chromium_service import render_pdf_with_chromium
from .services import render_report_html


def render_production_report_pdf(snapshot):
    """Generate final PDF from the same snapshot used by preview/archive."""
    html = render_report_html(snapshot)
    return render_pdf_with_chromium(html)
