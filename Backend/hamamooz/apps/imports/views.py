from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from hamamooz.apps.accounts.access import selected_school_ids, user_has_role
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.viewsets import AuditedModelViewSet
from hamamooz.apps.organizations.models import School

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
        for school_id in selected_school_ids(request)
        if user_has_role(request.user, SOURCE_MANAGERS, school_id=school_id)
    ]


class ImportJobViewSet(ModelViewSet):
    queryset = ImportJob.objects.all()
    parser_classes = [MultiPartParser]

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
        job = get_object_or_404(ImportJob, pk=pk)

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
        job = get_object_or_404(ImportJob, pk=pk)

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
        school_header = request.headers.get("X-School-ID")
        if not school_header:
            raise ValidationError({"X-School-ID": "برای اسکن پوشه داده الزامی است."})
        school = get_object_or_404(School, id=school_header)
        if school.id not in set(managed_source_school_ids(request)):
            raise ValidationError({"school": "به مدرسه انتخاب‌شده دسترسی ندارید."})
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
