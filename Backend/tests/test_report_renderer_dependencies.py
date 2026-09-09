from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_active_pdf_runtime_is_chromium_only():
    requirements = (BACKEND_ROOT / "requirements" / "base.txt").read_text()
    project = (BACKEND_ROOT / "pyproject.toml").read_text()
    lock = (BACKEND_ROOT / "uv.lock").read_text()
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text()
    rendering = (BACKEND_ROOT / "hamamooz" / "apps" / "reports" / "rendering.py").read_text()
    services = (BACKEND_ROOT / "hamamooz" / "apps" / "reports" / "services.py").read_text()

    active_files = (requirements, project, lock, dockerfile, rendering, services)
    assert all("weasyprint" not in content.lower() for content in active_files)
    assert "playwright==1.62.0" in requirements
    assert '"playwright==1.62.0"' in project
    assert 'name = "playwright"' in lock
    assert "playwright install --with-deps chromium" in dockerfile
    assert "render_report_html" not in rendering
    assert "render_to_string" not in services
    assert not (BACKEND_ROOT / "templates" / "reports" / "report_card.html").exists()
    assert not (
        BACKEND_ROOT
        / "hamamooz"
        / "apps"
        / "reports"
        / "templates"
        / "reports"
        / "report_card_chromium.html"
    ).exists()
