import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

ALLOWED_EVIDENCE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": {".jpg", ".jpeg"},
    b"\x89PNG\r\n\x1a\n": {".png"},
    b"RIFF": {".webp"},
}


def attendance_evidence_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    dated_path = timezone.localdate().strftime("%Y/%m")
    return f"attendance/evidence/{dated_path}/{uuid.uuid4().hex}{suffix}"


def _read_prefix(value, length=16):
    position = value.tell() if hasattr(value, "tell") else None
    try:
        if hasattr(value, "seek"):
            value.seek(0)
        return value.read(length)
    finally:
        if position is not None and hasattr(value, "seek"):
            value.seek(position)


def validate_attendance_evidence(value):
    if not value:
        return

    max_size = int(getattr(settings, "ATTENDANCE_MAX_EVIDENCE_SIZE", 5 * 1024 * 1024))
    if value.size > max_size:
        raise ValidationError(
            f"حجم مدرک غیبت نباید بیشتر از {max_size // (1024 * 1024)} مگابایت باشد."
        )

    suffix = Path(value.name).suffix.lower()
    if suffix not in ALLOWED_EVIDENCE_EXTENSIONS:
        raise ValidationError("فرمت مجاز مدرک: PDF، JPG، PNG یا WEBP است.")

    prefix = _read_prefix(value)
    if suffix == ".pdf":
        if not prefix.startswith(b"%PDF-"):
            raise ValidationError("فایل بارگذاری‌شده یک PDF معتبر نیست.")
        return

    valid_signature = False
    for signature, extensions in ALLOWED_IMAGE_SIGNATURES.items():
        if prefix.startswith(signature) and suffix in extensions:
            valid_signature = True
            break
    if suffix == ".webp" and prefix.startswith(b"RIFF"):
        valid_signature = len(prefix) >= 12 and prefix[8:12] == b"WEBP"
    if not valid_signature:
        raise ValidationError("ساختار فایل تصویر معتبر نیست.")
