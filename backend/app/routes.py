"""HTTP routes for the travel itinerary planner API."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from pydantic import ValidationError

from .ai_service import ItineraryGenerator
from .budget import estimate_category_costs
from .config import get_config
from .errors import BadRequestError, NotFoundError, ValidationError as AppValidationError
from .models import (
    Activity,
    BudgetBreakdown,
    DayPlan,
    DeleteTripResponse,
    GenerateItineraryResponse,
    HealthResponse,
    INTERESTS,
    Itinerary,
    SaveTripRequest,
    Trip,
    TripPreferences,
    TripSummary,
    UpdateTripRequest,
)
from .storage import TripStore, TripStoreError

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)

API_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _store() -> TripStore:
    return current_app.extensions["trip_store"]


def _generator() -> ItineraryGenerator:
    config = get_config()
    return ItineraryGenerator(
        api_key=config.gemini_api_key,
        model=config.gemini_model,
        max_retries=config.gemini_max_retries,
    )


def _json_body() -> dict:
    """Parse the request body as JSON, raising a friendly error when invalid."""
    if not request.data and not request.form:
        raise AppValidationError("A JSON request body is required.")
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception as exc:
        raise BadRequestError(f"The request body is not valid JSON: {exc}") from exc
    if payload is None:
        raise AppValidationError("A JSON request body is required.")
    if not isinstance(payload, dict):
        raise BadRequestError("The request body must be a JSON object.")
    return payload


def _parse_preferences(payload: dict, allow_past_dates: bool = False) -> TripPreferences:
    try:
        return TripPreferences(
            **payload, allow_past_dates=allow_past_dates
        )
    except ValidationError as exc:
        raise _as_app_validation_error(exc) from exc


def _as_app_validation_error(exc: ValidationError) -> AppValidationError:
    from .app_factory import _format_pydantic_errors

    return AppValidationError(
        "The trip preferences are not valid.", details=_format_pydantic_errors(exc)
    )


def _current_owner_id() -> str | None:
    """Resolve the owner of the request.

    When ``SUPABASE_JWT_SECRET`` is configured, the ``Authorization: Bearer``
    token is validated server-side and its ``sub`` claim is used as the owner
    id, so a user can only ever access their own trips. Otherwise the API runs
    in single-user mode and returns ``None`` (no ownership filter).
    """
    config = get_config()
    if not config.auth_enabled:
        return None

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None

    token = header.split(" ", 1)[1].strip()
    try:
        import jwt

        claims = jwt.decode(
            token,
            config.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_aud": False},
        )
    except Exception as exc:
        logger.info("Rejected invalid auth token: %s", exc)
        from .errors import AuthError

        raise AuthError("The access token is invalid or has expired.")

    return claims.get("sub")


# ---------------------------------------------------------------------------
# Service endpoints
# ---------------------------------------------------------------------------


@api_bp.get("/")
def index():
    """Check that the API is running."""
    return jsonify(
        {
            "status": "ok",
            "name": "Travel Itinerary Planner API",
            "version": API_VERSION,
            "docs": "/api/meta",
            "endpoints": [
                "GET /",
                "GET /health",
                "GET /api/meta",
                "POST /api/generate-itinerary",
                "POST /api/trips",
                "GET /api/trips",
                "GET /api/trips/<trip_id>",
                "PUT /api/trips/<trip_id>",
                "DELETE /api/trips/<trip_id>",
            ],
        }
    )


@api_bp.get("/health")
def health():
    """Health check with a safe snapshot of the active configuration."""
    config = get_config()
    payload = HealthResponse(
        status="healthy",
        version=API_VERSION,
        environment=config.public_snapshot(),
    )
    return jsonify(payload.model_dump(mode="json"))


@api_bp.get("/api/meta")
def meta():
    """Expose the option lists the frontend needs to build its form."""
    from .models import (
        AccommodationPreference,
        Currency,
        MAX_INTERESTS,
        MAX_TRIP_DAYS,
        MAX_TRAVELERS,
        TransportationPreference,
        TravelStyle,
    )

    return jsonify(
        {
            "interests": list(INTERESTS),
            "travel_styles": [item.value for item in TravelStyle],
            "accommodation_options": [item.value for item in AccommodationPreference],
            "transportation_options": [item.value for item in TransportationPreference],
            "currencies": [item.value for item in Currency],
            "limits": {
                "max_trip_days": MAX_TRIP_DAYS,
                "max_travelers": MAX_TRAVELERS,
                "max_interests": MAX_INTERESTS,
            },
        }
    )


# ---------------------------------------------------------------------------
# Itinerary generation
# ---------------------------------------------------------------------------


@api_bp.post("/api/generate-itinerary")
def generate_itinerary():
    """Generate a personalised day-by-day itinerary from trip preferences."""
    payload = _json_body()
    preferences = _parse_preferences(payload)

    generator = _generator()
    itinerary = generator.generate(preferences)

    response = GenerateItineraryResponse(
        itinerary=itinerary,
        preferences=preferences,
        meta={
            "generated_by": itinerary.generated_by,
            "model": get_config().gemini_model if itinerary.generated_by == "gemini" else None,
            "duration_days": preferences.duration_days,
            "disclaimer": itinerary.disclaimer,
        },
    )
    return jsonify(response.model_dump(mode="json"))


@api_bp.post("/api/estimate-budget")
def estimate_budget():
    """Estimate the cost split for a set of preferences without generating a plan."""
    payload = _json_body()
    preferences = _parse_preferences(payload)
    estimates = estimate_category_costs(preferences)

    from .budget import calculate_budget

    breakdown = calculate_budget(preferences, **estimates)
    return jsonify(
        {
            "breakdown": breakdown.model_dump(mode="json"),
            "estimates": estimates,
        }
    )


# ---------------------------------------------------------------------------
# Trip persistence
# ---------------------------------------------------------------------------


@api_bp.post("/api/trips")
def create_trip():
    """Save a generated trip."""
    payload = _json_body()

    try:
        request_model = SaveTripRequest(**payload)
    except ValidationError as exc:
        raise _as_app_validation_error(exc) from exc

    owner_id = _current_owner_id()
    trip = _store().save(
        preferences=request_model.preferences,
        itinerary=request_model.itinerary,
        title=request_model.title,
        notes=request_model.notes,
        owner_id=owner_id,
    )
    return jsonify(trip.model_dump(mode="json")), 201


@api_bp.get("/api/trips")
def list_trips():
    """Retrieve the user's saved trips."""
    owner_id = _current_owner_id()
    trips = _store().list(owner_id=owner_id)
    return jsonify({"trips": [trip.model_dump(mode="json") for trip in trips], "count": len(trips)})


@api_bp.get("/api/trips/<trip_id>")
def get_trip(trip_id: str):
    """Retrieve one trip."""
    owner_id = _current_owner_id()
    trip = _store().get(trip_id, owner_id=owner_id)
    if trip is None:
        raise NotFoundError(f"No trip was found with id '{trip_id}'.")
    return jsonify(trip.model_dump(mode="json"))


@api_bp.put("/api/trips/<trip_id>")
def update_trip(trip_id: str):
    """Update trip details (preferences, itinerary, title or notes)."""
    payload = _json_body()

    try:
        request_model = UpdateTripRequest(**payload)
    except ValidationError as exc:
        raise _as_app_validation_error(exc) from exc

    owner_id = _current_owner_id()

    try:
        trip = _store().update(
            trip_id=trip_id,
            preferences=request_model.preferences,
            itinerary=request_model.itinerary,
            title=request_model.title,
            notes=request_model.notes,
            owner_id=owner_id,
        )
    except TripStoreError as exc:
        raise NotFoundError(str(exc)) from exc

    return jsonify(trip.model_dump(mode="json"))


@api_bp.delete("/api/trips/<trip_id>")
def delete_trip(trip_id: str):
    """Delete a saved trip."""
    owner_id = _current_owner_id()
    deleted = _store().delete(trip_id, owner_id=owner_id)
    if not deleted:
        raise NotFoundError(f"No trip was found with id '{trip_id}'.")

    return jsonify(DeleteTripResponse(id=trip_id, deleted=True, message="Trip deleted.").model_dump(mode="json"))


@api_bp.post("/api/trips/<trip_id>/duplicate")
def duplicate_trip(trip_id: str):
    """Create a new trip from an existing trip's preferences."""
    owner_id = _current_owner_id()
    existing = _store().get(trip_id, owner_id=owner_id)
    if existing is None:
        raise NotFoundError(f"No trip was found with id '{trip_id}'.")
    if existing.preferences is None:
        raise AppValidationError("The source trip has no stored preferences to duplicate.")

    trip = _store().save(
        preferences=existing.preferences,
        itinerary=existing.itinerary or Itinerary(destination=existing.destination),
        title=f"{existing.title or existing.destination} (copy)",
        notes=existing.notes,
        owner_id=owner_id,
    )
    return jsonify(trip.model_dump(mode="json")), 201
