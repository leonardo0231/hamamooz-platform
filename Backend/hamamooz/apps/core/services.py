from ipaddress import ip_address

from django.conf import settings

from .models import AuditEvent

SENSITIVE_AUDIT_KEYS = {
    "password",
    "current_password",
    "new_password",
    "refresh",
    "access",
    "token",
    "secret",
    "authorization",
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


def redact_audit_data(value, key=""):
    if key.lower() in SENSITIVE_AUDIT_KEYS:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): redact_audit_data(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_audit_data(item) for item in value]
    if isinstance(value, tuple):
        return [redact_audit_data(item) for item in value]
    return value


def get_client_ip(request):
    if not request:
        return None
    forwarded = ""
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    value = forwarded or request.META.get("REMOTE_ADDR")
    try:
        return str(ip_address(value)) if value else None
    except ValueError:
        return None


def record_audit(
    *,
    action,
    actor=None,
    request=None,
    entity=None,
    organization_id=None,
    school_id=None,
    changes=None,
    metadata=None,
):
    return AuditEvent.objects.create(
        action=action,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        entity_type=entity._meta.label_lower if entity is not None else "",
        entity_id=str(entity.pk) if entity is not None else "",
        organization_id=organization_id,
        school_id=school_id,
        changes=redact_audit_data(changes or {}),
        metadata=redact_audit_data(metadata or {}),
        request_id=getattr(request, "request_id", "") if request else "",
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500] if request else "",
    )
