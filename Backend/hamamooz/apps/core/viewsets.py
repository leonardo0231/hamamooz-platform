from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from hamamooz.apps.accounts.permissions import RolePermission

from .services import record_audit
from .tenancy import object_organization_id, object_school_id


class AuditedModelViewSet(ModelViewSet):
    permission_classes = [RolePermission]

    audit_sensitive_fields = {
        "password",
        "current_password",
        "new_password",
        "refresh",
        "national_id",
        "phone",
        "phone_primary",
        "phone_secondary",
        "email",
        "address",
        "notes",
        "note",
        "reason",
        "absence_reason",
        "review_note",
        "message",
        "recipient",
    }

    @staticmethod
    def _audit_value(value):
        if isinstance(value, date | datetime | Decimal | UUID):
            return str(value)
        if hasattr(value, "pk"):
            return str(value.pk)
        if isinstance(value, str | int | float | bool) or value is None:
            return value
        return str(value)

    def _update_changes(self, serializer):
        fields = set(serializer.validated_data) - self.audit_sensitive_fields
        before = {
            field: self._audit_value(getattr(serializer.instance, field, None)) for field in fields
        }
        return fields, before

    def perform_audited_create(self, serializer, *, action="create", metadata=None, **kwargs):
        with transaction.atomic():
            instance = serializer.save(**kwargs)
            # Collection-level permission checks cannot safely infer the target tenant
            # from arbitrary request payloads. Re-check the persisted object in the same
            # transaction and roll it back if the requested scope and target differ.
            self.check_object_permissions(self.request, instance)
            audit_metadata = metadata(instance) if callable(metadata) else metadata
            record_audit(
                action=action,
                actor=self.request.user,
                request=self.request,
                entity=instance,
                organization_id=object_organization_id(instance),
                school_id=object_school_id(instance),
                metadata=audit_metadata,
            )
        return instance

    def perform_create(self, serializer):
        self.perform_audited_create(serializer)

    def perform_update(self, serializer):
        fields, before = self._update_changes(serializer)
        with transaction.atomic():
            instance = serializer.save()
            self.check_object_permissions(self.request, instance)
            after = {field: self._audit_value(getattr(instance, field, None)) for field in fields}
            record_audit(
                action="update",
                actor=self.request.user,
                request=self.request,
                entity=instance,
                organization_id=object_organization_id(instance),
                school_id=object_school_id(instance),
                changes={"before": before, "after": after},
            )

    def perform_destroy(self, instance):
        with transaction.atomic():
            record_audit(
                action="delete",
                actor=self.request.user,
                request=self.request,
                entity=instance,
                organization_id=object_organization_id(instance),
                school_id=object_school_id(instance),
            )
            try:
                instance.delete()
            except ProtectedError as exc:
                raise ValidationError(
                    {"detail": "این رکورد دارای داده‌های وابسته است و قابل حذف نیست."}
                ) from exc
