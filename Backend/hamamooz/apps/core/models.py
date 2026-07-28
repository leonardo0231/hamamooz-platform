import uuid

from django.conf import settings
from django.db import models
from django.db.models.deletion import ProtectedError
from django.utils import timezone


class TimeStampedUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        deleted = 0
        breakdown = {}
        for obj in self.iterator():
            count, details = obj.delete()
            deleted += count
            for label, value in details.items():
                breakdown[label] = breakdown.get(label, 0) + value
        return deleted, breakdown

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class ActiveManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    pass


class SoftDeleteModel(TimeStampedUUIDModel):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def _live_protected_relations(self):
        protected = []
        for relation in self._meta.related_objects:
            if relation.on_delete is not models.PROTECT:
                continue
            accessor = relation.get_accessor_name()
            manager = getattr(self, accessor, None)
            if manager is None:
                continue
            queryset = manager.all()
            if any(field.name == "is_deleted" for field in relation.related_model._meta.fields):
                queryset = queryset.filter(is_deleted=False)
            if queryset.exists():
                protected.extend(list(queryset[:20]))
        return protected

    def delete(self, using=None, keep_parents=False):
        if self.is_deleted:
            return 0, {self._meta.label: 0}
        protected = self._live_protected_relations()
        if protected:
            raise ProtectedError(
                "این رکورد به داده‌های فعال یا تاریخی وابسته است و قابل حذف نیست.",
                protected,
            )
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
        return 1, {self._meta.label: 1}

    def restore(self):
        if not self.is_deleted:
            return
        self.is_deleted = False
        self.deleted_at = None
        self.full_clean(exclude=["id"])
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])


class AuditEvent(TimeStampedUUIDModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    organization_id = models.UUIDField(null=True, blank=True, db_index=True)
    school_id = models.UUIDField(null=True, blank=True, db_index=True)
    action = models.CharField(max_length=100, db_index=True)
    entity_type = models.CharField(max_length=100, blank=True, db_index=True)
    entity_id = models.CharField(max_length=100, blank=True, db_index=True)
    changes = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["school_id", "-created_at"]),
            models.Index(fields=["actor", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.action} - {self.entity_type}:{self.entity_id}"
