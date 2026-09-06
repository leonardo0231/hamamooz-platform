from pathlib import Path

from django.conf import settings


class ChromiumPDFService:
    """Production PDF renderer using the Chromium rendering path.

    Keeps PDF generation isolated from report business logic so existing
    archive/report flows can migrate without breaking older exports.
    """

    def render(self, html: str) -> bytes:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright Chromium is required for production PDF rendering"
            ) from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            pdf = page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
            )
            browser.close()
            return pdf


def render_pdf_with_chromium(html: str) -> bytes:
    return ChromiumPDFService().render(html)
