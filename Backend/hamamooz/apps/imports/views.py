from io import BytesIO

from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from openpyxl import Workbook
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from hamamooz.apps.accounts.access import accessible_school_ids, user_has_role
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.viewsets import AuditedModelViewSet
from hamamooz.apps.organizations.models import Organization

from .data_directory import DataDirectoryScanner
from .dynamic_engine import inspect_uploaded_workbook
from .models import ClassSourceSelection, DataSourceConflict, DataSourceManifest, ImportJob
from .serializers import (
    ClassSourceSelectionSerializer,
    DataSourceConflictSerializer,
    DataSourceManifestSerializer,
    ImportJobCreateSerializer,
    ImportJobSerializer,
)
from .services.import_executor import ImportExecutor
from .tasks import process_import_job_task

SOURCE_MANAGERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
    Role.OPERATOR,
]


def managed_source_school_ids(request):
    """Source manifests contain national-ID conflict data; do not expose them to teachers."""

    return [
        school_id
        for school_id in accessible_school_ids(request.user)
        if user_has_role(request.user, SOURCE_MANAGERS, school_id=school_id)
    ]


class ImportJobViewSet(ModelViewSet):
    queryset = ImportJob.objects.all()
    parser_classes = [MultiPartParser]

    def get_queryset(self):
        return ImportJob.objects.filter(
            school_id__in=accessible_school_ids(self.request.user)
        ).select_related("organization", "school", "requested_by")

    def get_serializer_class(self):
        if self.action == "create":
            return ImportJobCreateSerializer
        return ImportJobSerializer

    def perform_create(self, serializer):
        """Queue the uploaded workbook after the database transaction commits."""

        job = serializer.save()
        transaction.on_commit(lambda: process_import_job_task.delay(str(job.id)))

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        job = get_object_or_404(self.get_queryset(), pk=pk)

        if job.status not in [ImportJob.Status.UPLOADED, ImportJob.Status.FAILED]:
            return Response({"detail": "Only uploaded imports can be analyzed."}, status=400)

        try:
            job.status = ImportJob.Status.ANALYZING
            job.save(update_fields=["status", "updated_at"])
            profile = inspect_uploaded_workbook(job.source_file.path)
            summary = {
                "students": 0,
                "classes": [],
                "indicators": len(profile.indicators),
                "periods": len(profile.periods),
                "sheets": profile.sheets,
            }
            job.preview_summary = summary
            job.status = ImportJob.Status.PREVIEW_READY
            job.errors = []
            job.save(update_fields=["status", "preview_summary", "errors", "updated_at"])
            return Response({"summary": summary, "warnings": [], "errors": []})
        except Exception as exc:
            job.status = ImportJob.Status.FAILED
            job.errors = [{"message": str(exc)}]
            job.save(update_fields=["status", "errors", "updated_at"])
            return Response({"summary": {}, "warnings": [], "errors": job.errors}, status=400)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        job = get_object_or_404(self.get_queryset(), pk=pk)

        if job.status != ImportJob.Status.PREVIEW_READY:
            return Response({"detail": "Only preview-ready imports can be confirmed."}, status=400)

        job.status = ImportJob.Status.CONFIRMED
        job.save(update_fields=["status", "updated_at"])

        try:
            summary = ImportExecutor(job).execute()
            return Response({"status": job.status, "summary": summary})
        except Exception as exc:
            job.status = ImportJob.Status.FAILED
            job.errors = [{"message": str(exc)}]
            job.save(update_fields=["status", "errors", "updated_at"])
            return Response({"errors": job.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        job = self.get_object()
        if job.status not in {ImportJob.Status.FAILED, ImportJob.Status.CANCELLED}:
            return Response(
                {"detail": "Only failed or cancelled imports can be retried."}, status=400
            )
        job.status = ImportJob.Status.QUEUED
        job.errors = []
        job.error_count = 0
        job.save(update_fields=["status", "errors", "error_count", "updated_at"])
        transaction.on_commit(lambda: process_import_job_task.delay(str(job.id)))
        return Response(ImportJobSerializer(job, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        job = self.get_object()
        if job.status not in {
            ImportJob.Status.QUEUED,
            ImportJob.Status.UPLOADED,
            ImportJob.Status.ANALYZING,
            ImportJob.Status.PREVIEW_READY,
            ImportJob.Status.CONFIRMED,
            ImportJob.Status.PROCESSING,
        }:
            return Response({"detail": "This import cannot be cancelled."}, status=400)
        job.status = ImportJob.Status.CANCELLED
        job.save(update_fields=["status", "updated_at"])
        return Response(ImportJobSerializer(job, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def errors(self, request, pk=None):
        job = self.get_object()
        workbook = Workbook()
        scope_sheet = workbook.active
        scope_sheet.title = "scope"
        scope_sheet.append(["مجموعه", job.organization.name])
        scope_sheet.append(["مدرسه", job.school.name])

        errors_sheet = workbook.create_sheet("errors")
        errors_sheet.append(["ردیف", "پیام"])
        for issue in job.errors or []:
            errors_sheet.append([issue.get("row"), issue.get("message", "")])

        stream = BytesIO()
        workbook.save(stream)
        stream.seek(0)
        return FileResponse(
            stream,
            as_attachment=True,
            filename="import-errors.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class DataSourceManifestViewSet(AuditedModelViewSet):
    """Protected inspection and rescan endpoint for repository Data/Excel files."""

    queryset = DataSourceManifest.objects.none()
    serializer_class = DataSourceManifestSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["school", "status"]
    search_fields = ["source_file"]
    required_roles_by_action = {"scan": SOURCE_MANAGERS}

    def get_queryset(self):
        return DataSourceManifest.objects.filter(
            school_id__in=managed_source_school_ids(self.request)
        ).select_related("school", "organization")

    @action(detail=False, methods=["post"])
    def scan(self, request):
        # Deliberately only scan the configured Data/Excel location.  Accepting a
        # client-controlled filesystem path here would turn an admin API into a
        # server file-disclosure primitive.
        school_id = next(iter(managed_source_school_ids(request)), None)
        if school_id is None:
            raise ValidationError({"detail": "مدرسه بعثت برای اسکن داده در دسترس نیست."})
        school = get_object_or_404(Organization, id=school_id, organization__isnull=False)
        result = DataDirectoryScanner(school).scan()
        return Response(result, status=status.HTTP_200_OK)


class DataSourceConflictViewSet(AuditedModelViewSet):
    queryset = DataSourceConflict.objects.none()
    serializer_class = DataSourceConflictSerializer
    http_method_names = ["get", "head", "options"]
    filterset_fields = ["school", "status", "conflict_type", "class_code", "national_id"]

    def get_queryset(self):
        return DataSourceConflict.objects.filter(
            school_id__in=managed_source_school_ids(self.request)
        ).prefetch_related("manifests")


class ClassSourceSelectionViewSet(AuditedModelViewSet):
    queryset = ClassSourceSelection.objects.none()
    serializer_class = ClassSourceSelectionSerializer
    filterset_fields = ["school", "class_code", "manifest"]
    required_roles_by_action = {
        action_name: SOURCE_MANAGERS
        for action_name in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return ClassSourceSelection.objects.filter(
            school_id__in=managed_source_school_ids(self.request)
        ).select_related("school", "manifest", "selected_by")

    def perform_create(self, serializer):
        self.perform_audited_create(serializer, selected_by=self.request.user)

    def perform_update(self, serializer):
        # Keep the original selector as audit evidence; AuditedModelViewSet records
        # the actual before/after manifest choice and request actor separately.
        super().perform_update(serializer)
