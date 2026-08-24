from copy import deepcopy

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from hamamooz.apps.accounts.access import allowed_class_ids, selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.services import record_audit
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import ReportArchive, ReportDraft, ReportTemplate
from .serializers import (
    ReportArchiveSerializer,
    ReportDraftContentSerializer,
    ReportDraftCreateSerializer,
    ReportDraftSerializer,
    ReportDraftTransitionSerializer,
    ReportPreviewSerializer,
    ReportTemplateSerializer,
)
from .services import (
    approve_report_draft,
    build_report_snapshot,
    render_report_draft,
    render_report_html,
    revalidate_report_draft,
)
from .tasks import generate_report_task

REPORTERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
    Role.OPERATOR,
    Role.TEACHER,
]
REPORT_REVIEWERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
]


def _safe_filename_part(value):
    return (
        str(value).replace("/", "-").replace("\\", "-").replace("\r", "").replace("\n", "").strip()
    )


class ReportArchiveViewSet(AuditedModelViewSet):
    queryset = ReportArchive.objects.none()
    serializer_class = ReportArchiveSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = [
        "school",
        "academic_year",
        "term",
        "layout_key",
        "report_type",
        "status",
        "enrollment",
        "class_section",
        "summer_program",
        "summer_registration",
    ]
    required_roles_by_action = {
        "create": REPORTERS,
        "preview": REPORTERS,
        "release": REPORT_REVIEWERS,
    }

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids(self.request.user, school_ids)
        queryset = ReportArchive.objects.filter(school_id__in=school_ids).filter(
            Q(class_section_id__in=class_ids)
            | Q(enrollment__class_section_id__in=class_ids)
            | Q(summer_registration__enrollment__class_section_id__in=class_ids)
        )
        return queryset.select_related(
            "school",
            "academic_year",
            "term",
            "enrollment__student",
            "class_section",
            "summer_program",
            "summer_registration__enrollment__student",
            "summer_exam",
            "requested_by",
        ).distinct()

    def perform_create(self, serializer):
        report = self.perform_audited_create(
            serializer,
            action="report.queued",
            metadata=lambda instance: {"report_type": instance.report_type},
        )
        transaction.on_commit(lambda: generate_report_task.delay(str(report.id)))

    @action(detail=False, methods=["post"])
    def preview(self, request):
        serializer = ReportPreviewSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        snapshot = build_report_snapshot(
            data["report_type"],
            data["term"],
            enrollment=data.get("enrollment"),
            class_section=data.get("class_section"),
        )
        return Response({"html": render_report_html(snapshot, preview=True), "snapshot": snapshot})

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        report = self.get_object()
        if report.status != ReportArchive.Status.COMPLETED or not report.output_file:
            return Response({"detail": "فایل گزارش هنوز آماده نیست."}, status=409)
        record_audit(
            action="report.downloaded",
            actor=request.user,
            request=request,
            entity=report,
            organization_id=report.organization_id,
            school_id=report.school_id,
        )
        report.output_file.open("rb")
        extension = "docx" if report.output_format == ReportArchive.OutputFormat.DOCX else "pdf"
        content_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if extension == "docx"
            else "application/pdf"
        )
        return FileResponse(
            report.output_file,
            as_attachment=True,
            filename=(
                f"{_safe_filename_part(report.organization.name)}-"
                f"{_safe_filename_part(report.school.name)}-"
                f"{_safe_filename_part(report.get_report_type_display())}-"
                f"{report.created_at:%Y-%m-%d}.{extension}"
            ),
            content_type=content_type,
        )

    @action(detail=True, methods=["get"], url_path="download-docx")
    def download_docx(self, request, pk=None):
        report = self.get_object()
        if report.status != ReportArchive.Status.COMPLETED or not report.editable_output_file:
            return Response({"detail": "نسخه قابل ویرایش هنوز آماده نیست."}, status=409)
        record_audit(
            action="report.editable_downloaded",
            actor=request.user,
            request=request,
            entity=report,
            organization_id=report.organization_id,
            school_id=report.school_id,
        )
        report.editable_output_file.open("rb")
        return FileResponse(
            report.editable_output_file,
            as_attachment=True,
            filename=(
                f"{_safe_filename_part(report.school.name)}-"
                f"{_safe_filename_part(report.period_label)}-editable.docx"
            ),
            content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        report = self.get_object()
        if report.status != ReportArchive.Status.COMPLETED:
            return Response({"detail": "Only a completed report may be released."}, status=409)
        if report.released_at:
            return Response(ReportArchiveSerializer(report, context={"request": request}).data)
        report.released_by = request.user
        report.released_at = timezone.now()
        report.save(update_fields=["released_by", "released_at", "updated_at"])
        record_audit(
            action="report.released",
            actor=request.user,
            request=request,
            entity=report,
            organization_id=report.organization_id,
            school_id=report.school_id,
        )
        return Response(ReportArchiveSerializer(report, context={"request": request}).data)


class ReportTemplateViewSet(AuditedModelViewSet):
    queryset = ReportTemplate.objects.none()
    serializer_class = ReportTemplateSerializer
    filterset_fields = ["organization", "school", "report_type", "output_format", "is_active"]
    search_fields = ["code", "title"]
    required_roles_by_action = {
        action_name: REPORT_REVIEWERS
        for action_name in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        from hamamooz.apps.accounts.access import accessible_organization_ids

        return ReportTemplate.objects.filter(
            organization_id__in=accessible_organization_ids(self.request.user)
        ).filter(Q(school__isnull=True) | Q(school_id__in=school_ids))

    def perform_destroy(self, instance):
        if instance.school_id is None:
            from hamamooz.apps.accounts.access import administered_organization_ids

            if instance.organization_id not in set(
                administered_organization_ids(self.request.user)
            ):
                raise PermissionDenied(
                    "Only an organization administrator may delete a shared template."
                )
        return super().perform_destroy(instance)


class ReportDraftViewSet(AuditedModelViewSet):
    queryset = ReportDraft.objects.none()
    serializer_class = ReportDraftSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = [
        "school",
        "academic_year",
        "term",
        "layout_key",
        "enrollment",
        "class_section",
        "summer_program",
        "summer_registration",
        "status",
    ]
    ordering_fields = ["created_at", "reviewed_at"]
    required_roles_by_action = {
        "create": REPORTERS,
        "partial_update": REPORTERS,
        "submit": REPORTERS,
        "approve": REPORT_REVIEWERS,
        "reject": REPORT_REVIEWERS,
        "render": REPORT_REVIEWERS,
    }

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids(self.request.user, school_ids)
        return (
            ReportDraft.objects.filter(school_id__in=school_ids)
            .filter(
                Q(enrollment__class_section_id__in=class_ids)
                | Q(class_section_id__in=class_ids)
                | Q(summer_registration__enrollment__class_section_id__in=class_ids)
            )
            .select_related(
                "template",
                "enrollment__student",
                "class_section",
                "summer_program",
                "summer_registration__enrollment__student",
                "summer_exam",
                "archive",
            )
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ReportDraftCreateSerializer
        return ReportDraftSerializer

    def create(self, request, *args, **kwargs):
        serializer = ReportDraftCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            draft = serializer.save()
            self.check_object_permissions(request, draft)
            record_audit(
                action="report.draft_created",
                actor=request.user,
                request=request,
                entity=draft,
                organization_id=draft.organization_id,
                school_id=draft.school_id,
                metadata={"template": draft.template.code, "snapshot_version": "report-card-v2"},
            )
        return Response(ReportDraftSerializer(draft).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        draft = self.get_object()
        if draft.status != ReportDraft.Status.DRAFT:
            raise PermissionDenied("Only a draft report may be edited.")
        serializer = ReportDraftContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        draft.content_overrides = serializer.validated_data["content_overrides"]
        draft.save(update_fields=["content_overrides", "updated_at"])
        record_audit(
            action="report.draft_edited",
            actor=request.user,
            request=request,
            entity=draft,
            organization_id=draft.organization_id,
            school_id=draft.school_id,
            metadata={"scope": "allowlisted_content_overrides"},
        )
        return Response(ReportDraftSerializer(draft).data)

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        """Render the tenant-scoped draft without bypassing official approval checks."""
        draft = self.get_object()
        snapshot = deepcopy(draft.snapshot)
        if draft.status in {ReportDraft.Status.DRAFT, ReportDraft.Status.SUBMITTED}:
            snapshot["content_overrides"] = dict(draft.content_overrides)
        return Response(
            {
                "html": render_report_html(snapshot, preview=True),
                "snapshot": snapshot,
                "warnings": snapshot.get("warnings", []),
            }
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        draft = self.get_object()
        if draft.status != ReportDraft.Status.DRAFT:
            return Response({"detail": "Only a draft report may be submitted."}, status=409)
        try:
            revalidate_report_draft(draft, require_ready=True)
        except (ValueError, serializers.ValidationError, DjangoValidationError) as exc:
            detail = getattr(exc, "detail", str(exc))
            return Response({"detail": detail}, status=409)
        draft.status = ReportDraft.Status.SUBMITTED
        draft.save(update_fields=["status", "updated_at"])
        record_audit(
            action="report.draft_submitted",
            actor=request.user,
            request=request,
            entity=draft,
            organization_id=draft.organization_id,
            school_id=draft.school_id,
        )
        return Response(ReportDraftSerializer(draft).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        draft = self.get_object()
        if draft.status != ReportDraft.Status.SUBMITTED:
            return Response({"detail": "Only a submitted report may be approved."}, status=409)
        try:
            draft = approve_report_draft(draft.id, actor=request.user)
        except (ValueError, serializers.ValidationError, DjangoValidationError) as exc:
            detail = getattr(exc, "detail", str(exc))
            return Response({"detail": detail}, status=409)
        record_audit(
            action="report.draft_approved",
            actor=request.user,
            request=request,
            entity=draft,
            organization_id=draft.organization_id,
            school_id=draft.school_id,
        )
        return Response(ReportDraftSerializer(draft).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        draft = self.get_object()
        if draft.status != ReportDraft.Status.SUBMITTED:
            return Response({"detail": "Only a submitted report may be rejected."}, status=409)
        serializer = ReportDraftTransitionSerializer(
            data={"target_status": "rejected", **request.data}
        )
        serializer.is_valid(raise_exception=True)
        draft.status = ReportDraft.Status.REJECTED
        draft.reviewed_by = request.user
        draft.reviewed_at = timezone.now()
        draft.rejection_reason = serializer.validated_data["rejection_reason"]
        draft.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"]
        )
        record_audit(
            action="report.draft_rejected",
            actor=request.user,
            request=request,
            entity=draft,
            organization_id=draft.organization_id,
            school_id=draft.school_id,
        )
        return Response(ReportDraftSerializer(draft).data)

    @action(detail=True, methods=["post"])
    def render(self, request, pk=None):
        draft = self.get_object()
        if draft.status != ReportDraft.Status.APPROVED:
            return Response({"detail": "Only an approved report may be rendered."}, status=409)
        try:
            rendered = render_report_draft(draft.id)
        except (ValueError, serializers.ValidationError, DjangoValidationError) as exc:
            detail = getattr(exc, "detail", str(exc))
            return Response({"detail": detail}, status=409)
        record_audit(
            action="report.draft_rendered",
            actor=request.user,
            request=request,
            entity=rendered,
            organization_id=rendered.organization_id,
            school_id=rendered.school_id,
        )
        return Response(ReportDraftSerializer(rendered).data)
