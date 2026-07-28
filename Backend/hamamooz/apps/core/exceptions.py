from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc)
        exc = DRFValidationError(detail=detail)
    response = exception_handler(exc, context)
    if response is None:
        return None
    request = context.get("request")
    request_id = getattr(request, "request_id", "")
    response.data = {
        "error": {
            "code": getattr(exc, "default_code", "error"),
            "detail": response.data,
            "request_id": request_id,
        }
    }
    return response
