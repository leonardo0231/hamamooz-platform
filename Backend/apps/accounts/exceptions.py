from rest_framework import status
from rest_framework.exceptions import APIException


class LoginTemporarilyLocked(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS

    default_detail = (
        "Unable to sign in. Try again later."
    )

    default_code = "login_temporarily_locked"