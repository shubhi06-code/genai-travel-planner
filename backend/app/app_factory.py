"""Flask application factory and JSON error handling."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from .config import Config, get_config
from .errors import AppError, DatabaseError, NotFoundError, ValidationError as AppValidationError
from .storage import LocalTripStore, SupabaseTripStore, TripStore

logger = logging.getLogger(__name__)

API_VERSION = "1.0.0"


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask application."""
    config: Config = get_config()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=config.secret_key,
        JSON_SORT_KEYS=False,
        TESTING=False,
        PROPAGATE_EXCEPTIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    CORS(
        app,
        resources={r"/api/*": {"origins": config.cors_origins}},
        supports_credentials=False,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    app.extensions["travel_config"] = config
    app.extensions["trip_store"] = _build_store(config)

    from .routes import api_bp

    app.register_blueprint(api_bp)

    _register_error_handlers(app)
    _register_request_logging(app)

    return app


def _build_store(config: Config) -> TripStore:
    """Return the Supabase store when configured, otherwise local SQLite."""
    if config.supabase_enabled:
        try:
            return SupabaseTripStore(
                config.supabase_url, config.supabase_key, config.supabase_trips_table
            )
        except DatabaseError:
            logger.exception(
                "Supabase is configured but unreachable - falling back to local storage."
            )
    return LocalTripStore(config.resolved_local_db_path)


def _register_request_logging(app: Flask) -> None:
    @app.after_request
    def log_request(response):  # noqa: ANN001
        if request.path not in {"/", "/health"}:
            logger.info(
                "%s %s -> %s", request.method, request.path, response.status_code
            )
        return response


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        if exc.status_code >= 500:
            logger.exception("Application error: %s", exc.message)
        return jsonify(exc.to_dict()), exc.status_code

    @app.errorhandler(ValidationError)
    def handle_pydantic_error(exc: ValidationError):
        return (
            jsonify(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "The request payload is not valid.",
                        "details": _format_pydantic_errors(exc),
                    }
                }
            ),
            422,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        code_map = {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            413: "payload_too_large",
            429: "rate_limited",
            500: "internal_error",
            503: "service_unavailable",
        }
        status = exc.code or 500
        return (
            jsonify(
                {
                    "error": {
                        "code": code_map.get(status, "http_error"),
                        "message": exc.description or exc.name,
                    }
                }
            ),
            status,
        )

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return (
            jsonify(
                {
                    "error": {
                        "code": "internal_error",
                        "message": "An unexpected error occurred. Please try again.",
                    }
                }
            ),
            500,
        )


def _format_pydantic_errors(exc: ValidationError) -> list[dict]:
    """Turn Pydantic errors into a frontend-friendly field list."""
    formatted = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", []) if part != "__root__"]
        formatted.append(
            {
                "field": ".".join(location) if location else "body",
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "value_error"),
            }
        )
    return formatted


__all__ = ["create_app", "API_VERSION", "NotFoundError", "AppValidationError"]
