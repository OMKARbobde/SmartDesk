import logging

from django.http import JsonResponse
from django.http import Http404
from django.views.csrf import csrf_failure as django_csrf_failure
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


logger = logging.getLogger(__name__)


def success_response(data, meta=None, status=200, headers=None):
    """Return the common SmartDesk success envelope."""
    return Response(
        {"data": data, "meta": meta or {}},
        status=status,
        headers=headers,
    )


class Conflict(exceptions.APIException):
    status_code = 409
    default_detail = "The request conflicts with the current resource state."
    default_code = "conflict"


def _has_detail_code(value, code):
    if getattr(value, "code", None) == code:
        return True
    if isinstance(value, dict):
        return any(_has_detail_code(item, code) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_detail_code(item, code) for item in value)
    return False


def _stringify_detail(value):
    if isinstance(value, dict):
        return {str(key): _stringify_detail(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [str(item) if not isinstance(item, (dict, list, tuple)) else _stringify_detail(item) for item in value]
    return str(value)


def _error_details(data):
    if isinstance(data, dict):
        return {str(key): _stringify_detail(value) if isinstance(value, (dict, list, tuple)) else [str(value)] for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return {"non_field_errors": [str(item) for item in data]}
    if data:
        return {"non_field_errors": [str(data)]}
    return {}


def api_exception_handler(exc, context):
    """Format DRF exceptions consistently, including unexpected API errors."""
    response = drf_exception_handler(exc, context)
    if response is None:
        request = context.get("request")
        logger.error(
            "Unhandled API exception on %s",
            getattr(request, "path", "<unknown>"),
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return Response(
            {"error": {
                "code": "server_error",
                "message": "An unexpected server error occurred.",
                "details": {},
            }},
            status=500,
        )

    data = response.data
    details = {}
    if isinstance(exc, exceptions.ValidationError):
        code = "ambiguous_identifier" if _has_detail_code(data, "ambiguous_identifier") else "validation_error"
        message = (
            "This identifier matches multiple accounts. Use the account username or contact an administrator."
            if code == "ambiguous_identifier"
            else "Request data is invalid."
        )
        details = _error_details(data)
    elif isinstance(exc, exceptions.AuthenticationFailed):
        code, message = "authentication_failed", "The supplied credentials are invalid."
    elif isinstance(exc, exceptions.NotAuthenticated):
        code, message = "not_authenticated", "Authentication is required."
    elif isinstance(exc, exceptions.PermissionDenied):
        detail = str(getattr(exc, "detail", ""))
        if detail.startswith("CSRF Failed:"):
            code, message = "csrf_failed", "CSRF validation failed. Refresh the security token and retry."
        else:
            code, message = "permission_denied", "You do not have permission to perform this action."
    elif isinstance(exc, (exceptions.NotFound, Http404)):
        code, message = "not_found", "The requested resource was not found."
    elif isinstance(exc, exceptions.MethodNotAllowed):
        code, message = "method_not_allowed", "This method is not allowed for the requested resource."
    elif isinstance(exc, Conflict):
        code, message = "conflict", "The request conflicts with the current resource state."
        details = {}
    elif response.status_code == 409:
        code, message = "conflict", "The request conflicts with the current resource state."
        details = {}
    else:
        code = getattr(exc, "default_code", "api_error")
        message = "The request could not be completed."

    response.data = {
        "error": {
            "code": str(code),
            "message": message,
            "details": details,
        }
    }
    return response


def csrf_failure(request, reason=""):
    """Return JSON CSRF errors for Step 3 endpoints, preserving other pages."""
    if request.path.startswith("/api/auth/") or request.path == "/api/users/me/":
        return JsonResponse(
            {"error": {
                "code": "csrf_failed",
                "message": "CSRF validation failed. Refresh the security token and retry.",
                "details": {},
            }},
            status=403,
        )
    return django_csrf_failure(request, reason=reason)
