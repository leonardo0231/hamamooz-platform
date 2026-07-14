from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
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
