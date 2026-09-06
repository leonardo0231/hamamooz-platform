from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .dynamic_engine import inspect_uploaded_workbook
from .models import ImportJob
from .serializers import ImportJobCreateSerializer, ImportJobSerializer


class ImportJobViewSet(ModelViewSet):
    queryset = ImportJob.objects.all()
    parser_classes = [MultiPartParser]

    def get_serializer_class(self):
        if self.action == "create":
            return ImportJobCreateSerializer
        return ImportJobSerializer

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        job = get_object_or_404(ImportJob, pk=pk)

        if job.status not in [
            ImportJob.Status.UPLOADED,
            ImportJob.Status.FAILED,
        ]:
            return Response(
                {"detail": "Only uploaded imports can be analyzed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

            return Response({
                "summary": summary,
                "warnings": [],
                "errors": [],
            })

        except Exception as exc:
            job.status = ImportJob.Status.FAILED
            job.errors = [{"message": str(exc)}]
            job.save(update_fields=["status", "errors", "updated_at"])

            return Response(
                {
                    "summary": {},
                    "warnings": [],
                    "errors": job.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        job = get_object_or_404(ImportJob, pk=pk)

        if job.status != ImportJob.Status.PREVIEW_READY:
            return Response(
                {"detail": "Only preview-ready imports can be confirmed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job.status = ImportJob.Status.CONFIRMED
        job.save(update_fields=["status", "updated_at"])
        return Response(ImportJobSerializer(job).data)
