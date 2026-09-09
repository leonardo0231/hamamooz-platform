import pytest


@pytest.mark.django_db
class TestReleaseImportReportPipeline:
    def test_import_states_are_documented(self):
        from hamamooz.apps.imports.models import ImportJob

        states = {choice[0] for choice in ImportJob.Status.choices}
        assert {
            "UPLOADED",
            "ANALYZING",
            "PREVIEW_READY",
            "CONFIRMED",
            "PROCESSING",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        }.issubset(states)

    def test_report_visual_contract_importable(self):
        from hamamooz.apps.reports import visuals

        assert visuals is not None

    def test_pdf_render_service_contract_importable(self):
        from hamamooz.apps.reports import rendering

        assert hasattr(rendering, "render_production_report_pdf")
