import re
import tempfile
from html import escape
from pathlib import Path

DEFAULT_TIMEOUT_MS = 30_000


class ReportRendererUnavailable(RuntimeError):
    """Raised when the approved Chromium report runtime is not available."""


def _with_base_url(document: str, base_url: str | None) -> str:
    """Make relative static/font URLs resolve from the Django application.

    The report HTML is written to a temporary directory before Chromium opens
    it.  Without a ``base`` element, a relative URL such as
    ``static/fonts/Estedad.woff2`` would be resolved below that temporary
    directory and the PDF would silently use fallback fonts.
    """

    if not base_url:
        return document

    base_tag = f'<base href="{escape(base_url, quote=True)}">'
    head = re.search(r"<head(?:\s[^>]*)?>", document, flags=re.IGNORECASE)
    if head:
        return f"{document[: head.end()]}{base_tag}{document[head.end() :]}"
    return f"{base_tag}{document}"


class ChromiumReportRenderer:
    """Production PDF renderer using headless Chromium.

    Keeps report rendering independent from Django templates and allows the
    frontend-quality HTML/CSS report layout to be exported identically.
    """

    def render(
        self,
        html: str,
        *,
        base_url: str | None = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> bytes:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ReportRendererUnavailable(
                "Chromium report rendering is unavailable: install Playwright and run "
                "'playwright install chromium' to provision the browser bundle."
            ) from exc

        with tempfile.TemporaryDirectory() as tmp:
            html_file = Path(tmp) / "report.html"
            html_file.write_text(_with_base_url(html, base_url), encoding="utf-8")

            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except Exception as exc:
                    raise ReportRendererUnavailable(
                        "Chromium report rendering is unavailable: the Playwright Chromium "
                        "executable is not installed or cannot be launched. Run "
                        "'playwright install chromium' and verify the runtime image."
                    ) from exc

                try:
                    # ``format`` is a PDF option, not a browser-page option.
                    page = browser.new_page()
                    page.emulate_media(media="print")
                    page.goto(
                        html_file.as_uri(),
                        wait_until="networkidle",
                        timeout=timeout_ms,
                    )
                    # Wait for local Estedad/Vazirmatn fonts before taking the
                    # snapshot; otherwise a fast print can capture fallback text.
                    page.evaluate("document.fonts ? document.fonts.ready : Promise.resolve()")
                    pdf = page.pdf(
                        format="A3",
                        landscape=True,
                        print_background=True,
                        prefer_css_page_size=True,
                    )
                except ReportRendererUnavailable:
                    raise
                except Exception as exc:
                    raise ReportRendererUnavailable(
                        "Chromium report rendering failed while loading or printing the "
                        "report. Check the Playwright/Chromium runtime and local assets."
                    ) from exc
                finally:
                    browser.close()

            return pdf
