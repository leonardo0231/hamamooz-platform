from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

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
        job.status = ImportJob.Status.ANALYZING
        job.save(update_fields=["status", "updated_at"])

        # Analyzer integration point. Existing dynamic_engine is called from
        # the executor layer in the next hardening step.
        job.preview_summary = {
            "students": 0,
            "classes": [],
            "indicators": 0,
            "periods": 0,
        }
        job.status = ImportJob.Status.PREVIEW_READY
        job.save(update_fields=["status", "preview_summary", "updated_at"])

        return Response({
            "summary": job.preview_summary,
            "warnings": [],
            "errors": [],
        })

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
