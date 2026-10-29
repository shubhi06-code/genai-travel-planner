"""Tests for the AI itinerary generation service (Gemini + fallback)."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from app.ai_service import ItineraryGenerator
from app.models import TripPreferences


def _prefs(**overrides) -> TripPreferences:
    start = date.today() + timedelta(days=1)
    payload = {
        "destination": "Lisbon, Portugal",
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=1)).isoformat(),
        "budget": 800.0,
        "currency": "EUR",
        "travelers": 2,
        "interests": ["food", "sightseeing"],
        "travel_style": "balanced",
        "accommodation": "mid-range",
        "transportation": "mixed",
    }
    payload.update(overrides)
    return TripPreferences(**payload)


def test_generator_without_api_key_uses_template_fallback():
    generator = ItineraryGenerator(api_key="", model="gemini-2.0-flash")

    itinerary = generator.generate(_prefs())

    assert itinerary.generated_by == "template-fallback"
    assert len(itinerary.days) == 2
    assert itinerary.destination == "Lisbon, Portugal"
    assert itinerary.days[0].activities


def test_fallback_creates_one_day_per_trip_day():
    generator = ItineraryGenerator(api_key="", model="gemini-2.0-flash")

    itinerary = generator.generate(_prefs(end_date=(date.today() + timedelta(days=4)).isoformat()))

    assert len(itinerary.days) == 4
    assert [day.day_number for day in itinerary.days] == [1, 2, 3, 4]


def test_fallback_respects_travel_style_pacing():
    relaxed = ItineraryGenerator(api_key="", model="m").generate(_prefs(travel_style="relaxed"))
    packed = ItineraryGenerator(api_key="", model="m").generate(_prefs(travel_style="packed"))

    assert len(packed.days[0].activities) > len(relaxed.days[0].activities)


def test_fallback_includes_meals_and_transport_notes():
    generator = ItineraryGenerator(api_key="", model="m")

    itinerary = generator.generate(_prefs())

    categories = {a.category for a in itinerary.days[0].activities}
    assert "food" in categories
    assert "transport" in categories


def test_fallback_budget_tracks_preferences():
    generator = ItineraryGenerator(api_key="", model="m")

    itinerary = generator.generate(_prefs(budget=1000.0))

    assert itinerary.budget.budget == 1000.0
    assert itinerary.budget.total > 0
    assert itinerary.budget.currency == "EUR"


def test_fallback_fits_the_plan_within_a_reasonable_budget():
    generator = ItineraryGenerator(api_key="", model="m")

    itinerary = generator.generate(_prefs(budget=900.0))

    assert itinerary.budget.total <= 900.0
    assert itinerary.budget.over_budget is False


def test_fallback_scales_down_a_generous_budget():
    generator = ItineraryGenerator(api_key="", model="m")

    itinerary = generator.generate(_prefs(budget=400.0))

    # 400 EUR is a tight but plausible budget for two people over two days.
    assert itinerary.budget.total <= 400.0


def test_fallback_reports_honestly_when_budget_is_impossible():
    generator = ItineraryGenerator(api_key="", model="m")

    itinerary = generator.generate(_prefs(budget=1.0))

    assert itinerary.budget.over_budget is True
    assert itinerary.budget.over_budget_amount > 0
    assert any("exceed" in note.lower() for note in itinerary.budget.notes)


def test_fallback_days_lead_with_different_activities():
    generator = ItineraryGenerator(api_key="", model="m")

    itinerary = generator.generate(
        _prefs(interests=["food", "museums", "nature"], end_date=(date.today() + timedelta(days=3)).isoformat())
    )

    openers = [day.activities[0].name for day in itinerary.days]
    assert len(set(openers)) == len(openers), f"days repeat the same opener: {openers}"
    assert len(openers) == 3


def test_fallback_day_summaries_differ():
    generator = ItineraryGenerator(api_key="", model="m")

    itinerary = generator.generate(
        _prefs(interests=["food", "museums", "nature"], end_date=(date.today() + timedelta(days=3)).isoformat())
    )

    summaries = [day.summary for day in itinerary.days]
    assert len(set(summaries)) == len(summaries)


def test_fallback_days_use_different_filler_activities():
    generator = ItineraryGenerator(api_key="", model="m")

    itinerary = generator.generate(
        _prefs(end_date=(date.today() + timedelta(days=3)).isoformat())
    )

    # Compare the set of activity names per day; days should not be identical.
    per_day = [tuple(a.name for a in day.activities) for day in itinerary.days]
    assert len(set(per_day)) == len(per_day)


def test_fallback_day_title_matches_day_theme():
    generator = ItineraryGenerator(api_key="", model="m")

    itinerary = generator.generate(
        _prefs(interests=["food", "museums", "nature"], end_date=(date.today() + timedelta(days=3)).isoformat())
    )

    for day in itinerary.days:
        # The theme word must also appear in the title (title-cased compare),
        # so the two never contradict each other.
        theme = day.theme.lower()
        title = day.title.lower()
        assert theme in title, f"theme '{day.theme}' not reflected in title '{day.title}'"


def test_fallback_reflects_interests_in_plan():
    generator = ItineraryGenerator(api_key="", model="m")

    itinerary = generator.generate(_prefs(interests=["museums", "history"]))

    text = json.dumps([a.description for a in itinerary.days[0].activities]).lower()
    assert any(word in text for word in ("museum", "histor", "heritage", "gallery"))


class _FakeModels:
    def __init__(self, text: str | None = None, error: Exception | None = None):
        self.text = text
        self.error = error
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error

        class _Resp:
            pass

        resp = _Resp()
        resp.text = self.text
        return resp


class _FakeClient:
    def __init__(self, models: _FakeModels):
        self.models = models


def _generator_with_fake(text: str | None = None, error: Exception | None = None):
    """Build a generator whose Gemini client is a controllable fake."""
    generator = ItineraryGenerator(api_key="fake-key", model="gemini-2.0-flash")
    models = _FakeModels(text=text, error=error)
    generator._client = _FakeClient(models)
    return generator, models


def test_generator_parses_gemini_json_response():
    generator, models = _generator_with_fake()

    payload = {
        "title": "2 Days in Lisbon",
        "summary": "A compact city break.",
        "days": [
            {
                "day_number": 1,
                "date": (date.today() + timedelta(days=1)).isoformat(),
                "title": "Old town",
                "summary": "Alfama walk",
                "activities": [
                    {
                        "name": "Castelo de Sao Jorge",
                        "description": "Hilltop castle with city views.",
                        "time": "10:00",
                        "duration": "2 h",
                        "location": "Alfama",
                        "category": "attraction",
                        "estimated_cost": 15.0,
                    }
                ],
                "meals": {"lunch": "Time Out Market"},
            }
        ],
        "travel_tips": ["Buy a transit card"],
        "packing_list": ["Comfortable shoes"],
    }
    models.text = json.dumps(payload)

    itinerary = generator.generate(_prefs())

    assert itinerary.generated_by == "gemini"
    assert itinerary.title == "2 Days in Lisbon"
    assert itinerary.days[0].activities[0].name == "Castelo de Sao Jorge"
    assert itinerary.days[0].activities[0].estimated_cost == 15.0
    assert itinerary.budget.total == 15.0


def test_generator_sends_the_preferences_to_gemini():
    generator, models = _generator_with_fake()
    models.text = json.dumps({"title": "T", "days": []})

    generator.generate(_prefs())

    prompt = models.calls[0]["contents"]
    assert "Lisbon, Portugal" in prompt
    assert "800.00 EUR" in prompt
    assert "2 day(s)" in prompt
    assert models.calls[0]["config"]["response_mime_type"] == "application/json"


def test_generator_strips_markdown_code_fences():
    generator, models = _generator_with_fake()
    models.text = (
        '```json\n'
        + json.dumps(
            {
                "title": "T",
                "days": [
                    {
                        "day_number": 1,
                        "title": "Day one",
                        "activities": [
                            {"name": "Walk", "category": "attraction", "estimated_cost": 5}
                        ],
                    }
                ],
            }
        )
        + '\n```'
    )

    itinerary = generator.generate(_prefs())

    assert itinerary.title == "T"
    assert itinerary.days[0].activities[0].name == "Walk"


def test_generator_falls_back_when_ai_raises():
    generator, models = _generator_with_fake(error=RuntimeError("API quota exhausted"))

    itinerary = generator.generate(_prefs())

    assert itinerary.generated_by == "template-fallback"
    assert len(itinerary.days) == 2


def test_generator_falls_back_when_ai_returns_garbage():
    generator, models = _generator_with_fake()
    models.text = "I am not JSON at all"

    itinerary = generator.generate(_prefs())

    assert itinerary.generated_by == "template-fallback"


def test_generator_handles_empty_days_from_ai():
    generator, models = _generator_with_fake()
    models.text = json.dumps({"title": "T", "days": []})

    itinerary = generator.generate(_prefs())

    assert len(itinerary.days) == 2
