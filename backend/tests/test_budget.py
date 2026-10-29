"""Tests for the budget calculation engine."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.budget import calculate_budget
from app.models import Activity, DayPlan, Itinerary, TripPreferences


def _prefs(**overrides) -> TripPreferences:
    start = date.today() + timedelta(days=1)
    payload = {
        "destination": "Lisbon",
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=2)).isoformat(),
        "budget": 900.0,
        "currency": "EUR",
        "travelers": 2,
    }
    payload.update(overrides)
    return TripPreferences(**payload)


def test_budget_totals_match_sum_of_categories():
    breakdown = calculate_budget(
        _prefs(),
        accommodation=300.0,
        food=200.0,
        activities=100.0,
        transport=50.0,
    )

    assert breakdown.accommodation == 300.0
    assert breakdown.food == 200.0
    assert breakdown.activities == 100.0
    assert breakdown.transport == 50.0
    assert breakdown.total == pytest.approx(650.0)


def test_per_person_cost_divides_by_traveler_count():
    breakdown = calculate_budget(
        _prefs(travelers=4),
        accommodation=400.0,
        food=200.0,
        activities=100.0,
        transport=100.0,
    )

    assert breakdown.total == pytest.approx(800.0)
    assert breakdown.per_person == pytest.approx(200.0)


def test_budget_remaining_is_positive_when_under_budget():
    breakdown = calculate_budget(
        _prefs(budget=1000.0),
        accommodation=200.0,
        food=150.0,
        activities=50.0,
        transport=50.0,
    )

    assert breakdown.over_budget is False
    assert breakdown.over_budget_amount == 0.0
    # 200 + 150 + 50 + 50 = 450 total, so 550 of the 1000 budget remains.
    assert breakdown.total == pytest.approx(450.0)
    assert breakdown.remaining == pytest.approx(550.0)
    assert breakdown.utilization_percent == pytest.approx(45.0)


def test_budget_flags_overrun_and_reports_amount():
    breakdown = calculate_budget(
        _prefs(budget=300.0),
        accommodation=200.0,
        food=150.0,
        activities=50.0,
        transport=50.0,
    )

    assert breakdown.over_budget is True
    assert breakdown.over_budget_amount == pytest.approx(150.0)
    assert breakdown.remaining == pytest.approx(-150.0)
    assert breakdown.utilization_percent == pytest.approx(150.0)
    assert any("exceed" in note.lower() for note in breakdown.notes)


def test_budget_note_added_when_nearly_exhausted():
    breakdown = calculate_budget(
        _prefs(budget=500.0),
        accommodation=200.0,
        food=150.0,
        activities=100.0,
        transport=30.0,
    )

    # 480 / 500 = 96% utilisation -> the plan is tight but not over budget.
    assert breakdown.over_budget is False
    assert breakdown.utilization_percent == pytest.approx(96.0)
    assert any("tight" in note.lower() for note in breakdown.notes)


def test_budget_currency_is_carried_through():
    breakdown = calculate_budget(
        _prefs(currency="JPY"),
        accommodation=0.0,
        food=0.0,
        activities=0.0,
        transport=0.0,
    )

    assert breakdown.currency == "JPY"


def test_budget_can_be_derived_from_itinerary_activities():
    itinerary = Itinerary(
        destination="Lisbon",
        days=[
            DayPlan(
                day_number=1,
                activities=[
                    Activity(name="Museum", estimated_cost=15.0, category="attraction"),
                    Activity(name="Lunch", estimated_cost=30.0, category="food"),
                    Activity(name="Taxi", estimated_cost=10.0, category="transport"),
                ],
            )
        ],
    )

    totals = calculate_budget_from_itinerary(_prefs(), itinerary)

    assert totals["activities"] == pytest.approx(15.0)
    assert totals["food"] == pytest.approx(30.0)
    assert totals["transport"] == pytest.approx(10.0)


def test_budget_handles_empty_itinerary():
    totals = calculate_budget_from_itinerary(_prefs(), Itinerary(destination="Lisbon"))

    assert totals == {"accommodation": 0.0, "food": 0.0, "activities": 0.0, "transport": 0.0}


# Imported late so the RED run fails on the missing symbol, not on a typo.
from app.budget import calculate_budget_from_itinerary  # noqa: E402
