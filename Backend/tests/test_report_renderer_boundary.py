import builtins
import sys
import types

import pytest

from hamamooz.apps.reports import rendering, services
from hamamooz.apps.reports.chromium_renderer import (
    ChromiumReportRenderer,
    ReportRendererUnavailable,
    _print_url,
    _snapshot_init_script,
    _with_base_url,
)


def test_production_boundary_uses_injected_renderer_and_application_base(monkeypatch):
    monkeypatch.setattr(services, "_pdf_snapshot", lambda snapshot: snapshot)
    monkeypatch.setattr(
        services,
        "render_report_html",
        lambda snapshot: "<html><head></head><body>report</body></html>",
    )
    calls = {}

    class FakeRenderer:
        def render(self, html, **kwargs):
            calls["html"] = html
            calls.update(kwargs)
            return b"%PDF-1.7\nfixture"

    pdf = rendering.render_production_report_pdf({"reports": []}, renderer=FakeRenderer())

    assert pdf.startswith(b"%PDF")
    assert calls["base_url"].startswith("file:")
    assert '<base href="file:' in _with_base_url(calls["html"], calls["base_url"])


def test_public_pdf_service_delegates_to_production_boundary(monkeypatch):
    calls = {}

    def fake_production_renderer(snapshot, *, renderer=None):
        calls["snapshot"] = snapshot
        calls["renderer"] = renderer
        return b"%PDF-1.7\nfixture"

    monkeypatch.setattr(rendering, "render_production_report_pdf", fake_production_renderer)
    injected = object()
    snapshot = {"reports": []}

    assert services.render_report_pdf(snapshot, renderer=injected).startswith(b"%PDF")
    assert calls == {"snapshot": snapshot, "renderer": injected}


def test_missing_playwright_is_reported_without_a_legacy_fallback(monkeypatch):
    real_import = builtins.__import__

    def block_playwright(name, *args, **kwargs):
        if name == "playwright" or name.startswith("playwright."):
            raise ImportError("playwright intentionally unavailable in this test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_playwright)

    with pytest.raises(ReportRendererUnavailable, match="[Pp]laywright|Chromium"):
        ChromiumReportRenderer().render("<html><body>report</body></html>")


def test_react_production_boundary_uses_snapshot_renderer(monkeypatch, settings):
    snapshot = {"reports": []}
    calls = {}

    monkeypatch.setattr(services, "_pdf_snapshot", lambda value: value)
    monkeypatch.setattr(
        services,
        "render_report_html",
        lambda value: pytest.fail("The production React path must not render Django HTML."),
    )

    class FakeRenderer:
        def render_snapshot(self, value, **kwargs):
            calls["snapshot"] = value
            calls.update(kwargs)
            return b"%PDF-1.7\nreact-fixture"

    monkeypatch.setattr(rendering, "ChromiumReportRenderer", FakeRenderer)
    settings.REPORT_FRONTEND_URL = "http://frontend:8080/report-sample.html?tenant=school"
    settings.REPORT_RENDER_TIMEOUT_MS = 45_000

    pdf = rendering.render_production_report_pdf(snapshot)

    assert pdf.startswith(b"%PDF")
    assert calls == {
        "snapshot": snapshot,
        "frontend_url": settings.REPORT_FRONTEND_URL,
        "timeout_ms": 45_000,
    }


def test_react_snapshot_inlines_only_authorized_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    logo = tmp_path / "school-logo.png"
    photo = tmp_path / "student-photo.jpg"
    logo.write_bytes(b"logo-bytes")
    photo.write_bytes(b"photo-bytes")
    snapshot = {
        "reports": [
            {
                "school": {"logo_url": "/media/school-logo.png"},
                "student": {"photo_url": "/media/student-photo.jpg"},
            }
        ]
    }

    prepared = rendering.prepare_react_snapshot(snapshot)
    report = prepared["reports"][0]

    assert report["school"]["logo_url"] == "data:image/png;base64,bG9nby1ieXRlcw=="
    assert report["student"]["photo_url"] == "data:image/jpeg;base64,cGhvdG8tYnl0ZXM="


def test_print_url_replaces_existing_print_mode_without_snapshot_data():
    assert _print_url("https://frontend/report-sample.html?print=0&tenant=school") == (
        "https://frontend/report-sample.html?tenant=school&print=1"
    )


def test_snapshot_init_script_escapes_html_and_marks_automation():
    script = _snapshot_init_script({"comment": "</script>&\u2028"})

    assert "</script>" not in script
    assert "\\u003c/script\\u003e\\u0026\\u2028" in script
    assert "globalThis.__REPORT_AUTOMATION__=true" in script


def test_render_snapshot_waits_for_react_readiness_before_printing(monkeypatch):
    calls = []

    class FakePage:
        def add_init_script(self, *, script):
            calls.append(("init", script))

        def emulate_media(self, *, media):
            calls.append(("media", media))

        def goto(self, url, **kwargs):
            calls.append(("goto", url, kwargs))

        def wait_for_function(self, expression, **kwargs):
            calls.append(("ready", expression, kwargs))

        def evaluate(self, expression):
            calls.append(("fonts", expression))
            if expression == "globalThis.__REPORT_ERROR__ || ''":
                return ""

        def pdf(self, **kwargs):
            calls.append(("pdf", kwargs))
            return b"%PDF-1.7\nreact-fixture"

    class FakeBrowser:
        def new_page(self):
            calls.append(("new_page",))
            return FakePage()

        def close(self):
            calls.append(("close",))

    class FakePlaywright:
        chromium = types.SimpleNamespace(launch=lambda **kwargs: FakeBrowser())

    class FakeContext:
        def __enter__(self):
            return FakePlaywright()

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: FakeContext()
    playwright = types.ModuleType("playwright")
    playwright.sync_api = sync_api
    monkeypatch.setitem(sys.modules, "playwright", playwright)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)

    pdf = ChromiumReportRenderer().render_snapshot(
        {"reports": []},
        frontend_url="http://frontend/report-sample.html?print=0",
        timeout_ms=1234,
    )

    assert pdf.startswith(b"%PDF")
    assert calls[0][0] == "new_page"
    assert calls[1][0] == "init"
    assert '__REPORT_SNAPSHOT__={"reports":[]}' in calls[1][1]
    assert calls[2] == ("media", "print")
    assert calls[3] == (
        "goto",
        "http://frontend/report-sample.html?print=1",
        {"wait_until": "domcontentloaded", "timeout": 1234},
    )
    assert calls[4][0] == "ready"
    assert calls[4][1] == "globalThis.__REPORT_READY__ === true || typeof globalThis.__REPORT_ERROR__ === 'string' && globalThis.__REPORT_ERROR__"
    assert calls[5] == ("fonts", "globalThis.__REPORT_ERROR__ || ''")
    assert calls[6][0] == "fonts"
    assert calls[7][0] == "pdf"
    assert calls[-1] == ("close",)
