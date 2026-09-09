from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from hamamooz.apps.accounts.access import accessible_school_ids

from .dynamic_engine import inspect_uploaded_workbook
from .models import ImportJob
from .serializers import (
    DataPathImportCreateSerializer,
    DataPathImportSerializer,
    ImportJobCreateSerializer,
    ImportJobSerializer,
)
from .services.import_executor import ImportExecutor
from .tasks import process_data_path_import_task, process_import_job_task


class ImportJobViewSet(ModelViewSet):
    queryset = ImportJob.objects.all()
    parser_classes = [MultiPartParser, JSONParser]

    def get_serializer_class(self):
        if self.action == "create":
            return ImportJobCreateSerializer
        return ImportJobSerializer

    def perform_create(self, serializer):
        """Queue the uploaded workbook after the database transaction commits."""

        job = serializer.save()
        transaction.on_commit(lambda: process_import_job_task.delay(str(job.id)))

    @extend_schema(
        request=DataPathImportCreateSerializer,
        responses={202: DataPathImportSerializer},
    )
    @action(detail=False, methods=["post"], url_path="from-data-path")
    def from_data_path(self, request):
        """Queue a server-side scan of the mounted repository Data folder."""

        serializer = DataPathImportCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data_import = serializer.save()
        transaction.on_commit(lambda: process_data_path_import_task.delay(str(data_import.id)))
        return Response(
            DataPathImportSerializer(data_import, context={"request": request}).data,
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={200: DataPathImportSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="data-path-imports")
    def data_path_imports(self, request):
        from .models import DataPathImport

        queryset = DataPathImport.objects.filter(school_id__in=accessible_school_ids(request.user))
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(
                DataPathImportSerializer(page, many=True, context={"request": request}).data
            )
        return Response(
            DataPathImportSerializer(
                queryset[:50], many=True, context={"request": request}
            ).data
        )

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
