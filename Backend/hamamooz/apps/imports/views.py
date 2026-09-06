from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from hamamooz.apps.accounts.access import selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import ImportJob
from .preview_service import build_import_preview
from .serializers import ImportJobCreateSerializer, ImportJobSerializer
from .serializers_preview import PreviewResponseSerializer
from .tasks import process_import_job_task

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

    required_roles_by_action = {
        "create": IMPORTERS,
        "preview": IMPORTERS,
        "retry": IMPORTERS,
        "cancel": IMPORTERS,
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
        )

    def perform_create(self, serializer):
        job = self.perform_audited_create(serializer, action="import.queued")
        transaction.on_commit(lambda: process_import_job_task.delay(str(job.id)))

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        job = self.get_object()
        job.status = ImportJob.Status.ANALYZING
        job.save(update_fields=["status", "updated_at"])
        preview = build_import_preview(job)
        job.preview_summary = preview
        job.status = ImportJob.Status.PREVIEW_READY
        job.save(update_fields=["preview_summary", "status", "updated_at"])
        return Response(preview)
