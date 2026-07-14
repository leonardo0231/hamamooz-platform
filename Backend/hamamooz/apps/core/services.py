from ipaddress import ip_address

from .models import AuditEvent


def get_client_ip(request):
    if not request:
        return None
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
        changes=changes or {},
        metadata=metadata or {},
        request_id=getattr(request, "request_id", "") if request else "",
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500] if request else "",
    )
