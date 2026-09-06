from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.http import FileResponse
from django.utils import timezone
from django.utils.text import slugify
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from openpyxl import Workbook
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from hamamooz.apps.accounts.access import allowed_class_ids, selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.viewsets import AuditedModelViewSet
from hamamooz.apps.organizations.models import ClassSection

from .comprehensive_template import build_comprehensive_school_template
from .models import ImportJob
from .serializers import ImportJobCreateSerializer, ImportJobSerializer
from .serializers_preview import PreviewResponseSerializer
from .tasks import process_import_job_task
from .templates import build_smart_evaluation_template
from .preview_service import build_import_preview

IMPORTERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
    Role.OPERATOR,
]


class ImportJobViewSet(AuditedModelViewSet):
    queryset = ImportJob.objects.none()
    serializer_class = ImportJobSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["school", "import_type", "status"]
    required_roles_by_action = {
        "create": IMPORTERS,
        "retry": IMPORTERS,
        "cancel": IMPORTERS,
        "template": IMPORTERS,
        "errors": IMPORTERS,
        "preview": IMPORTERS,
    }

    def get_serializer_class(self):
        if self.action == "create":
            return ImportJobCreateSerializer
        if self.action == "preview":
            return PreviewResponseSerializer
        return ImportJobSerializer

    def get_queryset(self):
        return ImportJob.objects.filter(
            school_id__in=selected_school_ids(self.request)
        ).select_related("school", "organization", "requested_by")

    def perform_create(self, serializer):
        job = self.perform_audited_create(
            serializer,
            action="import.queued",
            metadata=lambda instance: {
                "type": instance.import_type,
                "checksum": instance.checksum,
            },
        )
        transaction.on_commit(lambda: process_import_job_task.delay(str(job.id)))

    @extend_schema(
        responses={200: PreviewResponseSerializer}
    )
    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        job = self.get_object()

        if job.status not in [
            ImportJob.Status.UPLOADED,
            ImportJob.Status.PREVIEW_READY,
            ImportJob.Status.FAILED,
        ]:
            return Response(
                {"detail": "Import job is not available for preview."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job.status = ImportJob.Status.ANALYZING
        job.save(update_fields=["status", "updated_at"])

        try:
            preview = build_import_preview(job)
            job.preview_summary = preview
            job.status = ImportJob.Status.PREVIEW_READY
            job.save(update_fields=["preview_summary", "status", "updated_at"])
            return Response(preview)
        except Exception as exc:
            job.status = ImportJob.Status.FAILED
            job.errors = [{"message": str(exc)[:1000]}]
            job.save(update_fields=["status", "errors", "updated_at"])
            return Response(
                {"detail": "Preview generation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
