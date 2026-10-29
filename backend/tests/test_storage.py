"""Tests for the trip storage abstraction (local SQLite + Supabase adapter)."""

from __future__ import annotations

import pytest

from app.models import Itinerary, TripPreferences
from app.storage import LocalTripStore, TripStoreError


@pytest.fixture
def store(local_db_env):
    return LocalTripStore(local_db_env)


def _prefs() -> TripPreferences:
    from datetime import date, timedelta

    start = date.today() + timedelta(days=1)
    return TripPreferences(
        destination="Porto",
        start_date=start.isoformat(),
        end_date=(start + timedelta(days=1)).isoformat(),
        budget=500.0,
        currency="EUR",
        travelers=1,
        interests=["food"],
        travel_style="relaxed",
        accommodation="hostel",
        transportation="walking",
    )


def _itinerary() -> Itinerary:
    return Itinerary(destination="Porto", title="Porto weekend", summary="Short trip.")


def test_saving_a_trip_returns_an_id(store):
    trip = store.save(_prefs(), _itinerary())

    assert trip.id
    assert trip.destination == "Porto"
    assert trip.status in {"upcoming", "ongoing", "past"}


def test_saved_trip_can_be_fetched(store):
    saved = store.save(_prefs(), _itinerary())

    fetched = store.get(saved.id)

    assert fetched is not None
    assert fetched.id == saved.id
    assert fetched.preferences.destination == "Porto"
    assert fetched.itinerary.title == "Porto weekend"


def test_fetching_missing_trip_returns_none(store):
    assert store.get("missing-id") is None


def test_listing_returns_saved_trips(store):
    store.save(_prefs(), _itinerary())

    trips = store.list()

    assert len(trips) == 1
    assert trips[0].destination == "Porto"


def test_listing_filters_by_owner(store):
    store.save(_prefs(), _itinerary(), owner_id="user-a")

    assert len(store.list(owner_id="user-a")) == 1
    assert store.list(owner_id="user-b") == []


def test_updating_trip_changes_stored_values(store):
    saved = store.save(_prefs(), _itinerary())

    updated = store.update(saved.id, title="Updated title", notes="Bring a camera")

    assert updated.title == "Updated title"
    assert updated.notes == "Bring a camera"
    assert store.get(saved.id).title == "Updated title"


def test_updating_missing_trip_raises(store):
    with pytest.raises(TripStoreError):
        store.update("missing-id", title="x")


def test_deleting_trip_removes_it(store):
    saved = store.save(_prefs(), _itinerary())

    assert store.delete(saved.id) is True
    assert store.get(saved.id) is None


def test_deleting_missing_trip_returns_false(store):
    assert store.delete("missing-id") is False


def test_trip_status_is_past_for_old_dates(store):
    from datetime import date, timedelta

    past = date.today() - timedelta(days=5)
    prefs = TripPreferences(
        destination="Rome",
        start_date=past.isoformat(),
        end_date=(past + timedelta(days=1)).isoformat(),
        budget=300.0,
        travelers=1,
        allow_past_dates=True,
    )

    saved = store.save(prefs, _itinerary())

    assert saved.status == "past"


def test_trip_status_is_upcoming_for_future_dates(store):
    saved = store.save(_prefs(), _itinerary())

    assert saved.status == "upcoming"


def test_store_persists_across_instances(local_db_env):
    first = LocalTripStore(local_db_path=local_db_env)
    saved = first.save(_prefs(), _itinerary())

    second = LocalTripStore(local_db_path=local_db_env)

    assert second.get(saved.id) is not None
