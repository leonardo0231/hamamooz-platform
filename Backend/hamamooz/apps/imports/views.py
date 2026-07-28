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
    required_roles_by_action = {
        "create": IMPORTERS,
        "retry": IMPORTERS,
        "cancel": IMPORTERS,
        "template": IMPORTERS,
        "errors": IMPORTERS,
    }

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
        stale = (
            job.status == ImportJob.Status.PROCESSING
            and job.started_at
            and job.started_at
            < timezone.now() - timedelta(minutes=settings.IMPORT_PROCESSING_TIMEOUT_MINUTES)
        )
        if job.status != ImportJob.Status.FAILED and not stale:
            return Response(
                {"detail": "فقط Import ناموفق یا پردازش منقضی‌شده قابل تکرار است."},
                status=400,
            )
        job.status = ImportJob.Status.QUEUED
        job.save(update_fields=["status", "updated_at"])
        transaction.on_commit(lambda: process_import_job_task.delay(str(job.id)))
        return Response(self.get_serializer(job).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        job = self.get_object()
        if job.status not in [ImportJob.Status.QUEUED, ImportJob.Status.PROCESSING]:
            return Response(
                {"detail": "فقط Import در صف یا در حال پردازش قابل لغو است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        job.status = ImportJob.Status.CANCELLED
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at", "updated_at"])
        return Response(self.get_serializer(job).data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="template_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                enum=[choice.value for choice in ImportJob.ImportType],
            )
        ],
        responses={
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes
        },
    )
    @action(detail=False, methods=["get"], url_path=r"templates/(?P<template_type>[^/.]+)")
    def template(self, request, template_type=None):
        valid_types = {choice.value for choice in ImportJob.ImportType}
        if template_type not in valid_types:
            return Response(
                {"detail": "نوع Template معتبر نیست."}, status=status.HTTP_404_NOT_FOUND
            )
        template_path = (
            Path(settings.BASE_DIR) / "docs" / "import_templates" / f"{template_type}_template.xlsx"
        )
        if not template_path.exists():
            return Response(
                {"detail": "Template هنوز تولید نشده است."}, status=status.HTTP_404_NOT_FOUND
            )
        return FileResponse(
            template_path.open("rb"),
            as_attachment=True,
            filename=f"{slugify(template_type)}_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @action(detail=True, methods=["get"])
    def errors(self, request, pk=None):
        job = self.get_object()
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "errors"
        sheet.append(["row", "message"])
        for item in job.errors or []:
            sheet.append([item.get("row"), item.get("message", "")])
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return FileResponse(
            output,
            as_attachment=True,
            filename=f"{slugify(str(job.id))}_errors.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
