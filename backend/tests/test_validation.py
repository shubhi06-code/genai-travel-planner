"""Tests for request validation rules."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.models import MAX_TRIP_DAYS, TripPreferences


def _base(**overrides) -> dict:
    start = date.today() + timedelta(days=1)
    payload = {
        "destination": "Kyoto",
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=1)).isoformat(),
        "budget": 500.0,
        "currency": "USD",
        "travelers": 2,
        "interests": ["food"],
        "travel_style": "balanced",
        "accommodation": "mid-range",
        "transportation": "mixed",
    }
    payload.update(overrides)
    return payload


def test_valid_preferences_are_accepted():
    prefs = TripPreferences(**_base())

    assert prefs.destination == "Kyoto"
    assert prefs.duration_days == 2
    assert prefs.travelers == 2


def test_empty_destination_is_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(**_base(destination="   "))


def test_negative_budget_is_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(**_base(budget=-10))


def test_zero_budget_is_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(**_base(budget=0))


def test_zero_travelers_is_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(**_base(travelers=0))


def test_fractional_travelers_is_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(**_base(travelers=1.5))


def test_end_date_before_start_date_is_rejected():
    start = date.today() + timedelta(days=3)
    with pytest.raises(ValidationError):
        TripPreferences(
            **_base(
                start_date=start.isoformat(),
                end_date=(start - timedelta(days=1)).isoformat(),
            )
        )


def test_past_start_date_is_rejected_for_new_trips():
    past = date.today() - timedelta(days=2)
    with pytest.raises(ValidationError):
        TripPreferences(
            **_base(start_date=past.isoformat(), end_date=past.isoformat())
        )


def test_past_start_date_is_allowed_when_editing_existing_trip():
    past = date.today() - timedelta(days=2)
    prefs = TripPreferences(
        **_base(start_date=past.isoformat(), end_date=past.isoformat()),
        allow_past_dates=True,
    )

    assert prefs.start_date == past


def test_duration_longer_than_max_is_rejected():
    start = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError):
        TripPreferences(
            **_base(
                start_date=start.isoformat(),
                end_date=(start + timedelta(days=MAX_TRIP_DAYS)).isoformat(),
            )
        )


def test_same_day_trip_is_allowed():
    start = date.today() + timedelta(days=1)
    prefs = TripPreferences(
        **_base(start_date=start.isoformat(), end_date=start.isoformat())
    )

    assert prefs.duration_days == 1


def test_unknown_travel_style_is_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(**_base(travel_style="ultra-ultra-packed"))


def test_unknown_accommodation_is_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(**_base(accommodation="spaceship"))


def test_unknown_transportation_is_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(**_base(transportation="teleportation"))


def test_unknown_currency_is_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(**_base(currency="XYZ"))


def test_interests_are_normalised_and_deduplicated():
    prefs = TripPreferences(**_base(interests=["Food", "food", "Sight_Seeing", "  "]))

    assert prefs.interests == ["food", "sight-seeing"]


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(**_base(surprise="value"))


def test_duration_is_inclusive_of_both_endpoints():
    start = date.today() + timedelta(days=1)
    prefs = TripPreferences(
        **_base(start_date=start.isoformat(), end_date=(start + timedelta(days=4)).isoformat())
    )

    assert prefs.duration_days == 5
