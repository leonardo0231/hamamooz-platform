from pathlib import Path
import tempfile

from django.conf import settings


class ChromiumReportRenderer:
    """Production PDF renderer using headless Chromium.

    Keeps report rendering independent from Django templates and allows the
    frontend-quality HTML/CSS report layout to be exported identically.
    """

    def render(self, html: str) -> bytes:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "playwright is required for Chromium report rendering"
            ) from exc

        with tempfile.TemporaryDirectory() as tmp:
            html_file = Path(tmp) / "report.html"
            html_file.write_text(html, encoding="utf-8")

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(format="A4")
                page.goto(html_file.as_uri(), wait_until="networkidle")
                pdf = page.pdf(
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                )
                browser.close()

            return pdf
