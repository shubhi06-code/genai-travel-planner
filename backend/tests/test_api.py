"""API-level tests for every endpoint required by the specification."""

from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# Service level endpoints
# ---------------------------------------------------------------------------
def test_root_endpoint_reports_api_is_running(client):
    response = client.get("/")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert "name" in payload
    assert "version" in payload


def test_health_endpoint_returns_environment_snapshot(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "healthy"
    assert payload["environment"]["ai_provider"] in {"gemini", "template-fallback"}
    assert payload["environment"]["storage_backend"] in {"supabase", "local-sqlite"}
    assert "timestamp" in payload


# ---------------------------------------------------------------------------
# Itinerary generation
# ---------------------------------------------------------------------------
def test_generate_itinerary_returns_days_and_budget(client, sample_preferences):
    response = client.post("/api/generate-itinerary", json=sample_preferences)

    assert response.status_code == 200
    payload = response.get_json()
    assert "itinerary" in payload
    itinerary = payload["itinerary"]
    assert itinerary["destination"] == "Lisbon, Portugal"
    assert len(itinerary["days"]) == 3
    assert itinerary["days"][0]["activities"]
    assert itinerary["budget"]["total"] > 0
    assert itinerary["budget"]["currency"] == "EUR"
    assert payload["preferences"]["travelers"] == 2


def test_generate_itinerary_rejects_invalid_budget(client, sample_preferences):
    sample_preferences["budget"] = -5

    response = client.post("/api/generate-itinerary", json=sample_preferences)

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"


def test_generate_itinerary_rejects_missing_destination(client, sample_preferences):
    del sample_preferences["destination"]

    response = client.post("/api/generate-itinerary", json=sample_preferences)

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_error"


def test_generate_itinerary_rejects_past_start_date(client, sample_preferences):
    sample_preferences["start_date"] = "2000-01-01"
    sample_preferences["end_date"] = "2000-01-03"

    response = client.post("/api/generate-itinerary", json=sample_preferences)

    assert response.status_code == 422


def test_generate_itinerary_rejects_malformed_json(client):
    response = client.post(
        "/api/generate-itinerary", data="{not json", content_type="application/json"
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "bad_request"


def test_generate_itinerary_warns_when_over_budget(client, sample_preferences):
    sample_preferences["budget"] = 1.0

    response = client.post("/api/generate-itinerary", json=sample_preferences)

    assert response.status_code == 200
    budget = response.get_json()["itinerary"]["budget"]
    assert budget["over_budget"] is True
    assert budget["over_budget_amount"] > 0
    assert budget["notes"]


# ---------------------------------------------------------------------------
# Trip persistence
# ---------------------------------------------------------------------------
def test_save_trip_then_list_and_fetch(client, sample_preferences):
    generated = client.post("/api/generate-itinerary", json=sample_preferences)
    itinerary = generated.get_json()["itinerary"]

    save = client.post(
        "/api/trips",
        json={"preferences": sample_preferences, "itinerary": itinerary},
    )
    assert save.status_code == 201
    trip_id = save.get_json()["id"]

    listing = client.get("/api/trips")
    assert listing.status_code == 200
    trips = listing.get_json()["trips"]
    assert len(trips) == 1
    assert trips[0]["id"] == trip_id
    assert trips[0]["destination"] == "Lisbon, Portugal"

    detail = client.get(f"/api/trips/{trip_id}")
    assert detail.status_code == 200
    assert detail.get_json()["itinerary"]["days"]


def test_fetch_unknown_trip_returns_404(client):
    response = client.get("/api/trips/does-not-exist")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_update_trip_preferences(client, sample_preferences):
    generated = client.post("/api/generate-itinerary", json=sample_preferences)
    itinerary = generated.get_json()["itinerary"]
    trip_id = client.post(
        "/api/trips",
        json={"preferences": sample_preferences, "itinerary": itinerary},
    ).get_json()["id"]

    updated_prefs = dict(sample_preferences)
    updated_prefs["budget"] = 1500.0
    updated_prefs["notes"] = "Prefer quieter neighbourhoods"

    update = client.put(
        f"/api/trips/{trip_id}",
        json={"preferences": updated_prefs, "title": "Lisbon long weekend"},
    )
    assert update.status_code == 200
    assert update.get_json()["title"] == "Lisbon long weekend"
    assert update.get_json()["preferences"]["budget"] == 1500.0


def test_update_unknown_trip_returns_404(client):
    response = client.put("/api/trips/nope", json={"title": "x"})

    assert response.status_code == 404


def test_delete_trip_removes_it(client, sample_preferences):
    generated = client.post("/api/generate-itinerary", json=sample_preferences)
    itinerary = generated.get_json()["itinerary"]
    trip_id = client.post(
        "/api/trips",
        json={"preferences": sample_preferences, "itinerary": itinerary},
    ).get_json()["id"]

    deleted = client.delete(f"/api/trips/{trip_id}")
    assert deleted.status_code == 200
    assert deleted.get_json()["deleted"] is True

    assert client.get(f"/api/trips/{trip_id}").status_code == 404
    assert client.get("/api/trips").get_json()["trips"] == []


def test_delete_unknown_trip_returns_404(client):
    response = client.delete("/api/trips/missing")

    assert response.status_code == 404


def test_trips_list_is_empty_initially(client):
    response = client.get("/api/trips")

    assert response.status_code == 200
    assert response.get_json()["trips"] == []


def test_save_trip_rejects_invalid_preferences(client, sample_preferences):
    sample_preferences["travelers"] = 0

    response = client.post(
        "/api/trips",
        json={"preferences": sample_preferences, "itinerary": {"days": []}},
    )

    assert response.status_code == 422


def test_unsupported_method_returns_405(client):
    response = client.patch("/api/trips")

    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == "method_not_allowed"


def test_unknown_route_returns_404_json(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_cors_preflight_is_allowed(client):
    response = client.options(
        "/api/generate-itinerary",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code in (200, 204)
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"


def test_response_is_json_serialisable(client, sample_preferences):
    response = client.post("/api/generate-itinerary", json=sample_preferences)

    json.loads(response.get_data(as_text=True))
