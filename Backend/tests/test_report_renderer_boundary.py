import builtins

import pytest

from hamamooz.apps.reports import rendering, services
from hamamooz.apps.reports.chromium_renderer import (
    ChromiumReportRenderer,
    ReportRendererUnavailable,
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
