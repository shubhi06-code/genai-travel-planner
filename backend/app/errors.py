"""Application level errors and their JSON representation."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for errors that should be returned to the client."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, details: Any = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.details = details
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self) -> dict:
        payload: dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details is not None:
            payload["error"]["details"] = self.details
        return payload


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class AIServiceError(AppError):
    """Raised when the AI provider fails in a way we cannot recover from."""

    status_code = 502
    code = "ai_service_error"


class DatabaseError(AppError):
    status_code = 503
    code = "database_error"


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"
