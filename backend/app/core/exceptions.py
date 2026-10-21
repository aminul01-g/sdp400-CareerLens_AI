"""The single error envelope and its handlers.

Every error leaving this application has the same shape::

    {
      "error": {
        "code": "validation_error",
        "message": "Request validation failed.",
        "errors": [ {"field": "email", "message": "value is not a valid email"} ]
      }
    }

The important property is the last one: **no raw Python exception text, no
traceback and no SQL fragment ever reaches a client.** The legacy app returned
upstream provider error text straight from ``guidance.py:59``; that is finding S8
in the plan's security register and this module is its fix.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.exceptions")


class APIError(Exception):
    """Base class for every deliberate, client-visible failure."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        errors: list[dict[str, str]] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.errors = errors or []
        super().__init__(self.message)

    def to_payload(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "errors": self.errors,
            }
        }


class NotFoundError(APIError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "The requested resource does not exist."


class ConflictError(APIError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    message = "The request conflicts with the current state of the resource."


class ForbiddenError(APIError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"
    message = "You do not have permission to perform this action."


class UnauthorizedError(APIError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"
    message = "Authentication is required to access this resource."


class UnprocessableError(APIError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"
    message = "The request could not be processed as submitted."


class UnsupportedMediaTypeError(APIError):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    code = "unsupported_media_type"
    message = "That file type is not supported."


class PayloadTooLargeError(APIError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    code = "payload_too_large"
    message = "The uploaded file is too large."


class FeatureDisabledError(APIError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "feature_disabled"
    message = "This optional feature is not enabled."


class UpstreamError(APIError):
    """A third-party service the application depends on failed.

    The AI layer is the only part of the system that calls an external
    provider, and the provider's own error text is never returned: it can
    echo the request, and the request carries the user's document. The client
    is told that the feature is temporarily unavailable and nothing more.
    """

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "upstream_unavailable"
    message = (
        "The AI service is temporarily unavailable. Please try again shortly."
    )


class BadRequestError(APIError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"
    message = "The request is malformed."


class TooManyRequestsError(APIError):
    """The caller is going too fast.

    ``retry_after`` is the number of seconds the caller should wait, and it is
    sent as the standard ``Retry-After`` header so a well-behaved client does
    not have to guess.
    """

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"
    message = "Too many requests. Please wait a moment and try again."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        errors: list[dict[str, str]] | None = None,
        retry_after: int = 60,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code, errors=errors)
        self.retry_after = max(1, int(retry_after))


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    errors: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "errors": errors or []}},
        headers=headers,
    )


def _flatten_validation_errors(exc: RequestValidationError) -> list[dict[str, str]]:
    """Turn Pydantic's error list into ``{field, message}`` pairs the UI can bind."""
    flattened: list[dict[str, str]] = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", ()) if part != "body"]
        field = ".".join(location) if location else "body"
        message = error.get("msg", "Invalid value.")
        # Pydantic prefixes custom value errors with "Value error, "; strip it so
        # the client shows the message a person wrote, not a Pydantic artefact.
        if message.startswith("Value error, "):
            message = message[len("Value error, ") :]
        flattened.append({"field": field, "message": message})
    return flattened


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every handler to the application."""

    @app.exception_handler(APIError)
    async def _api_error_handler(_: Request, exc: APIError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        if isinstance(exc, TooManyRequestsError):
            # The standard header, so a client knows how long to wait without
            # parsing the message.
            headers = {**(headers or {}), "Retry-After": str(exc.retry_after)}
        return _error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            errors=exc.errors,
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            message="One or more fields are invalid.",
            errors=_flatten_validation_errors(exc),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_handler(_: Request, exc: IntegrityError) -> JSONResponse:
        # Log the detail for the operator; return a generic message so no SQL
        # text (table names, constraint names, column values) reaches the client.
        logger.warning("IntegrityError: %s", exc.orig, extra={"kind": "integrity_error"})
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            code="conflict",
            message="The request conflicts with data that already exists.",
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        code = {
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
        }.get(exc.status_code, "http_error")
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return _error_response(
            status_code=exc.status_code,
            code=code,
            message=detail,
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        # The traceback goes to the log, never to the client. This is the single
        # most important line in the module for finding S8.
        logger.exception(
            "Unhandled error on %s %s", request.method, request.url.path, extra={"kind": "unhandled"}
        )
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_error",
            message="An unexpected error occurred. Please try again.",
        )
