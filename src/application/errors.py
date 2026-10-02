"""Build safe, actionable failures shared by tools and the chat harness.

Provider details stay out of public results. This module owns the common error
shape so tool failures remain readable by both the model and the browser.
"""

from typing import cast

import httpx
from pydantic import JsonValue, ValidationError

from src.configuration.constants import ErrorCode


def create_error_result(
    code: ErrorCode,
    message: str,
    suggested_action: str,
) -> dict[str, JsonValue]:
    """Describe a failed operation without leaking exception contents."""
    return {"ok": False, "error": {
        "code": code.value,
        "message": message,
        "suggested_action": suggested_action,
    }}


def classify_external_failure(error: Exception) -> dict[str, JsonValue]:
    """Map HTTP and transport failures to stable codes, never raw bodies."""
    status = getattr(error, "status_code", None)
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
    if status in (401, 403):
        return create_error_result(ErrorCode.ACCESS_DENIED,
            "The external service denied access.", "Ask the app owner to check credentials and permissions.")
    if status == 429:
        return create_error_result(ErrorCode.RATE_LIMITED,
            "The external service is receiving too many requests.", "Wait a little and try again.")
    if isinstance(status, int) and 400 <= status < 500:
        return create_error_result(ErrorCode.BAD_REQUEST,
            "The external service rejected the request.", "Check the supplied details; if correct, contact the app owner.")
    if isinstance(error, (TimeoutError, httpx.TimeoutException)) or "Timeout" in type(error).__name__:
        return create_error_result(ErrorCode.TIMEOUT,
            "The request timed out.", "Try the unfinished request again.")
    if isinstance(status, int) and status >= 500 or isinstance(error, httpx.TransportError):
        return create_error_result(ErrorCode.SERVICE_UNAVAILABLE,
            "The external service is unavailable.", "Try again later.")
    if isinstance(error, ValueError):
        return create_error_result(ErrorCode.INVALID_RESPONSE,
            "The external service returned an unreadable response.", "Try again later.")
    return create_error_result(ErrorCode.SERVICE_UNAVAILABLE,
        "The external request could not be completed.", "Please try again or contact the app owner.")



def describe_validation_failure(error: ValidationError) -> dict[str, JsonValue]:
    """Expose field locations and validation advice without raw input values."""
    issues = []
    for issue in error.errors(include_input=False, include_url=False, include_context=False):
        location = ".".join(str(part) for part in cast(tuple[str | int, ...], issue["loc"]))
        issues.append(f"{location}: {issue['msg']}")
    return create_error_result(ErrorCode.INVALID_INPUT, "; ".join(issues), "Correct these fields and try again.")
