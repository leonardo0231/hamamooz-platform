from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_active_pdf_runtime_is_chromium_only():
    requirements = (BACKEND_ROOT / "requirements" / "base.txt").read_text()
    project = (BACKEND_ROOT / "pyproject.toml").read_text()
    lock = (BACKEND_ROOT / "uv.lock").read_text()
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text()
    template = (BACKEND_ROOT / "templates" / "reports" / "report_card.html").read_text()

    active_files = (requirements, project, lock, dockerfile, template)
    assert all("weasyprint" not in content.lower() for content in active_files)
    assert "playwright==1.62.0" in requirements
    assert '"playwright==1.62.0"' in project
    assert 'name = "playwright"' in lock
    assert "playwright install --with-deps chromium" in dockerfile
