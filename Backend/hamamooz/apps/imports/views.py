from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response

from hamamooz.apps.accounts.access import selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import ImportJob
from .serializers import ImportJobSerializer
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
    filterset_fields = ["school", "import_type", "status"]
    required_roles_by_action = {"create": IMPORTERS, "retry": IMPORTERS}

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

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        job = self.get_object()
        if job.status != ImportJob.Status.FAILED:
            return Response({"detail": "فقط Import ناموفق قابل تکرار است."}, status=400)
        job.status = ImportJob.Status.QUEUED
        job.save(update_fields=["status", "updated_at"])
        transaction.on_commit(lambda: process_import_job_task.delay(str(job.id)))
        return Response(self.get_serializer(job).data)
