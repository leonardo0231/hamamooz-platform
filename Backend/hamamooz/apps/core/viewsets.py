from rest_framework.viewsets import ModelViewSet

from hamamooz.apps.accounts.permissions import RolePermission

from .services import record_audit
from .tenancy import object_organization_id, object_school_id


class AuditedModelViewSet(ModelViewSet):
    permission_classes = [RolePermission]

    def perform_create(self, serializer):
        instance = serializer.save()
        record_audit(
            action="create",
            actor=self.request.user,
            request=self.request,
            entity=instance,
            organization_id=object_organization_id(instance),
            school_id=object_school_id(instance),
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        record_audit(
            action="update",
            actor=self.request.user,
            request=self.request,
            entity=instance,
            organization_id=object_organization_id(instance),
            school_id=object_school_id(instance),
        )

    def perform_destroy(self, instance):
        record_audit(
            action="delete",
            actor=self.request.user,
            request=self.request,
            entity=instance,
            organization_id=object_organization_id(instance),
            school_id=object_school_id(instance),
        )
        instance.delete()
