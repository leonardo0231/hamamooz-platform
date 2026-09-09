import json
import re
import tempfile
from html import escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DEFAULT_TIMEOUT_MS = 30_000


def _print_url(url: str) -> str:
    """Return a report entry URL with the print mode enabled.

    The snapshot is deliberately not encoded into this URL.  Apart from
    making the URL unwieldy, putting student data in a query string would
    expose it to browser history, access logs, and referrer headers.
    """

    value = str(url or "").strip()
    if not value:
        raise ValueError("A React report frontend URL is required.")
    parts = urlsplit(value)
    query = [(key, item) for key, item in parse_qsl(parts.query, keep_blank_values=True)]
    query = [(key, item) for key, item in query if key != "print"]
    query.append(("print", "1"))
    return urlunsplit(parts._replace(query=urlencode(query)))


def _snapshot_init_script(snapshot: dict) -> str:
    """Build the init script used to pass an authorized snapshot to React.

    The JSON is escaped for JavaScript context even though Playwright injects
    it as a script rather than parsing it as HTML.  This keeps the boundary
    safe if a student/school text contains a closing-tag-like sequence or a
    Unicode line separator.
    """

    payload = json.dumps(
        snapshot,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    payload = (
        payload.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    return f"globalThis.__REPORT_SNAPSHOT__={payload};globalThis.__REPORT_AUTOMATION__=true;"


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

            try:
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
            except ReportRendererUnavailable:
                raise
            except Exception as exc:
                raise ReportRendererUnavailable(
                    "Chromium report rendering is unavailable: the Playwright driver or "
                    "Chromium runtime failed to start. Verify the installed browser bundle."
                ) from exc

            return pdf

    def render_snapshot(
        self,
        snapshot: dict,
        *,
        frontend_url: str,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> bytes:
        """Render the compiled React report entry with an authorized snapshot.

        ``report-sample.html`` is the single browser report entry used for
        interactive print and server-side archive generation.  Playwright
        injects the already-authorized snapshot before the React module runs,
        then waits for the entry's explicit readiness marker before printing.
        No Django/Jinja report template participates in this production path.
        """

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ReportRendererUnavailable(
                "Chromium report rendering is unavailable: install Playwright and run "
                "'playwright install chromium' to provision the browser bundle."
            ) from exc

        target_url = _print_url(frontend_url)
        init_script = _snapshot_init_script(snapshot)

        try:
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
                    page = browser.new_page()
                    page.add_init_script(script=init_script)
                    page.emulate_media(media="print")
                    # The explicit readiness marker covers fonts and images.  Waiting only
                    # for DOMContentLoaded also works when the configured frontend is a
                    # development server that keeps an HMR connection open.
                    page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    page.wait_for_function(
                        "globalThis.__REPORT_READY__ === true || typeof globalThis.__REPORT_ERROR__ === 'string' && globalThis.__REPORT_ERROR__",
                        timeout=timeout_ms,
                    )
                    report_error = page.evaluate("globalThis.__REPORT_ERROR__ || ''")
                    if report_error:
                        raise ReportRendererUnavailable(
                            f"Chromium React report assets are unavailable: {report_error}"
                        )
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
                        "Chromium React report rendering failed while loading or printing the "
                        "report. Check REPORT_FRONTEND_URL, the report bundle, and local assets."
                    ) from exc
                finally:
                    browser.close()
        except ReportRendererUnavailable:
            raise
        except Exception as exc:
            raise ReportRendererUnavailable(
                "Chromium report rendering is unavailable: the Playwright driver or Chromium "
                "runtime failed to start. Verify the installed browser bundle."
            ) from exc

        if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF"):
            raise RuntimeError("The Chromium React report renderer returned invalid PDF bytes.")
        return pdf
