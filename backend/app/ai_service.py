"""AI itinerary generation.

The service talks to Google Gemini through the official ``google-genai`` SDK.
When no API key is configured - or when the provider errors out - it degrades
gracefully to a deterministic template generator so the application always
returns a usable, well-formed itinerary.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta
from typing import Any

from .budget import calculate_budget, calculate_budget_from_itinerary
from .models import (
    Activity,
    DayPlan,
    Itinerary,
    TripPreferences,
)

logger = logging.getLogger(__name__)

#: Pacing -> number of planned items per day.
PACING = {
    "relaxed": 4,
    "balanced": 5,
    "packed": 7,
    "adventure": 6,
    "cultural": 5,
    "romantic": 5,
    "family-friendly": 5,
}

SYSTEM_PROMPT = """You are an expert travel planner. You build precise, realistic,
day-by-day itineraries that respect the traveller's budget, pace and interests.

Rules:
- Return ONLY valid JSON. No markdown, no commentary, no code fences.
- Use realistic, well-known places and neighbourhood-level detail where possible.
- Estimate costs in the requested currency and keep the whole trip within budget.
- Schedule 3-7 activities per day plus meals, with sensible travel time between them.
- Respect the travel style: relaxed = slow days with rests, packed = many activities.
- Never invent specific opening hours as facts; phrase them as "typically around".
"""

RESPONSE_SCHEMA_HINT = """{
  "title": "3 Days in Lisbon",
  "summary": "Two to four sentences describing the trip.",
  "days": [
    {
      "day_number": 1,
      "date": "YYYY-MM-DD",
      "title": "Alfama and the riverfront",
      "theme": "Old town walking",
      "summary": "What this day is about.",
      "activities": [
        {
          "name": "Castelo de Sao Jorge",
          "description": "Two to four sentences about what to do there.",
          "time": "10:00",
          "duration": "2 h",
          "location": "Alfama, Lisbon",
          "category": "attraction",
          "estimated_cost": 15.0,
          "cost_note": "Adult ticket, approx.",
          "tip": "Go early to avoid queues.",
          "transport_note": "12 min walk from the tram stop."
        }
      ],
      "meals": {"breakfast": "...", "lunch": "...", "dinner": "..."},
      "notes": "Anything to remember for this day."
    }
  ],
  "travel_tips": ["..."],
  "packing_list": ["..."]
}"""


def build_user_prompt(preferences: TripPreferences) -> str:
    """Turn validated preferences into a detailed generation prompt."""
    interests = ", ".join(preferences.interests) if preferences.interests else "general sightseeing"
    nights = max(0, preferences.duration_days - 1)
    per_person = round(float(preferences.budget) / max(1, preferences.travelers), 2)

    lines = [
        f"Destination: {preferences.destination}",
        f"Trip length: {preferences.duration_days} day(s) ({nights} night(s)), "
        f"{preferences.start_date.isoformat()} to {preferences.end_date.isoformat()}",
        f"Travellers: {preferences.travelers}",
        f"Total budget: {preferences.budget:.2f} {preferences.currency.value} "
        f"(about {per_person:.2f} {preferences.currency.value} per person)",
        f"Travel style / pace: {preferences.travel_style.value}",
        f"Accommodation preference: {preferences.accommodation.value}",
        f"Transportation preference: {preferences.transportation.value}",
        f"Interests: {interests}",
    ]
    if preferences.notes:
        lines.append(f"Extra requests from the traveller: {preferences.notes}")

    lines += [
        "",
        "Budget guidance for your estimates:",
        f"- Accommodation is roughly 35-45% of the total budget.",
        f"- Food is roughly 18-25% of the total budget.",
        f"- Activities and entrance fees are roughly 15-25% of the total budget.",
        f"- Local transport and transfers are roughly 10-18% of the total budget.",
        "",
        f"Produce exactly {preferences.duration_days} day(s) in the "
        '"days" array, numbered from 1.',
        "",
        "Respond with JSON in exactly this shape:",
        RESPONSE_SCHEMA_HINT,
    ]
    return "\n".join(lines)


def _strip_code_fences(text: str) -> str:
    """Remove markdown fences and extract the JSON object from a model reply."""
    if not text:
        return ""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


class _UnrecoverableAIError(RuntimeError):
    """Raised when the AI response is unusable and retrying will not help."""


class ItineraryGenerator:
    """Generates an :class:`Itinerary` using Gemini, with a safe fallback."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", max_retries: int = 2):
        self.api_key = (api_key or "").strip()
        self.model = model or "gemini-2.0-flash"
        self.max_retries = max(0, int(max_retries))
        self._client: Any = None

        if self.api_key:
            try:
                from google import genai

                self._client = genai.Client(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover - SDK import guard
                logger.warning("Google Gen AI SDK unavailable: %s", exc)
                self._client = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def client(self) -> Any:
        """Lazily create the Gemini client (kept as a property for testability)."""
        if self._client is None and self.api_key:
            try:
                from google import genai

                self._client = genai.Client(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover
                logger.warning("Could not create Gemini client: %s", exc)
                self._client = None
        return self._client

    def generate(self, preferences: TripPreferences) -> Itinerary:
        """Generate an itinerary, falling back to the template on any failure."""
        if self.client is not None:
            for attempt in range(self.max_retries + 1):
                try:
                    return self._generate_with_gemini(preferences)
                except _UnrecoverableAIError:
                    # A well-formed but unusable response will not improve on a
                    # retry, so fall back to the template immediately.
                    break
                except Exception as exc:
                    logger.warning(
                        "Gemini generation failed (attempt %s/%s): %s",
                        attempt + 1,
                        self.max_retries + 1,
                        exc,
                    )
                    if attempt >= self.max_retries:
                        break

        logger.info("Falling back to the template itinerary generator.")
        return self._generate_fallback(preferences)

    # ------------------------------------------------------------------
    # Gemini path
    # ------------------------------------------------------------------
    def _generate_with_gemini(self, preferences: TripPreferences) -> Itinerary:
        client = self.client
        if client is None:  # pragma: no cover - guarded by caller
            raise RuntimeError("Gemini client is not available.")

        prompt = build_user_prompt(preferences)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.7,
                "top_p": 0.95,
                "max_output_tokens": 8192,
                "response_mime_type": "application/json",
            },
        )

        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini returned an empty response.")

        data = json.loads(_strip_code_fences(text))
        itinerary = self._itinerary_from_payload(data, preferences)
        if not itinerary.days:
            raise _UnrecoverableAIError("Gemini returned an itinerary without any days.")
        return itinerary

    def _itinerary_from_payload(
        self, data: dict[str, Any], preferences: TripPreferences
    ) -> Itinerary:
        days: list[DayPlan] = []
        raw_days = data.get("days") or []

        for index, raw_day in enumerate(raw_days):
            if not isinstance(raw_day, dict):
                continue
            day_number = int(raw_day.get("day_number") or index + 1)
            day_date = None
            raw_date = raw_day.get("date")
            if raw_date:
                try:
                    day_date = date.fromisoformat(str(raw_date)[:10])
                except ValueError:
                    day_date = preferences.start_date + timedelta(days=index)

            activities = [
                self._activity_from_payload(item)
                for item in (raw_day.get("activities") or [])
                if isinstance(item, dict)
            ]

            meals = raw_day.get("meals") if isinstance(raw_day.get("meals"), dict) else {}

            days.append(
                DayPlan(
                    day_number=day_number,
                    date=day_date,
                    title=str(raw_day.get("title") or f"Day {day_number}"),
                    theme=str(raw_day.get("theme") or ""),
                    summary=str(raw_day.get("summary") or ""),
                    activities=activities,
                    meals={str(k): str(v) for k, v in meals.items()},
                    notes=str(raw_day.get("notes") or ""),
                )
            )

        itinerary = Itinerary(
            title=str(data.get("title") or f"{preferences.duration_days} days in {preferences.destination}"),
            summary=str(data.get("summary") or ""),
            destination=preferences.destination,
            start_date=preferences.start_date,
            end_date=preferences.end_date,
            duration_days=preferences.duration_days,
            travelers=preferences.travelers,
            currency=preferences.currency.value,
            days=days,
            travel_tips=[str(t) for t in (data.get("travel_tips") or []) if t],
            packing_list=[str(p) for p in (data.get("packing_list") or []) if p],
            generated_by="gemini",
        )

        totals = calculate_budget_from_itinerary(preferences, itinerary)
        itinerary.budget = calculate_budget(preferences, **totals)
        for day in itinerary.days:
            day.daily_estimated_cost = round(
                sum(float(a.estimated_cost or 0) for a in day.activities), 2
            )
        return itinerary

    @staticmethod
    def _activity_from_payload(raw: dict[str, Any]) -> Activity:
        try:
            cost = float(raw.get("estimated_cost") or 0)
        except (TypeError, ValueError):
            cost = 0.0

        category = str(raw.get("category") or "other").lower()
        allowed = {
            "attraction",
            "food",
            "accommodation",
            "transport",
            "leisure",
            "shopping",
            "other",
        }
        if category not in allowed:
            category = "other"

        return Activity(
            name=str(raw.get("name") or "Activity"),
            description=str(raw.get("description") or ""),
            time=str(raw.get("time") or ""),
            duration=str(raw.get("duration") or ""),
            location=str(raw.get("location") or ""),
            category=category,  # type: ignore[arg-type]
            estimated_cost=max(0.0, cost),
            cost_note=str(raw.get("cost_note") or ""),
            tip=str(raw.get("tip") or ""),
            transport_note=str(raw.get("transport_note") or ""),
            is_estimate=True,
        )

    # ------------------------------------------------------------------
    # Deterministic fallback path
    # ------------------------------------------------------------------
    def _generate_fallback(self, preferences: TripPreferences) -> Itinerary:
        from .budget import estimate_category_costs
        from .templates import build_template_itinerary

        itinerary = build_template_itinerary(preferences)

        # Scale the per-activity estimates so the plan fits the stated budget
        # whenever that is possible. The floors keep the plan meaningful: a
        # budget that cannot cover even a minimum viable trip still produces
        # an honest over-budget warning.
        itinerary = _fit_to_budget(itinerary, preferences)

        totals = calculate_budget_from_itinerary(preferences, itinerary)
        itinerary.budget = calculate_budget(preferences, **totals)

        # If the template produced no priced activities (very small budgets),
        # fall back to the preference-based estimates so the user still sees a
        # meaningful budget breakdown.
        if itinerary.budget.total <= 0:
            estimates = estimate_category_costs(preferences)
            itinerary.budget = calculate_budget(preferences, **estimates)

        for day in itinerary.days:
            day.daily_estimated_cost = round(
                sum(float(a.estimated_cost or 0) for a in day.activities), 2
            )

        itinerary.generated_by = "template-fallback"
        return itinerary


#: Minimum fraction of an activity's original estimate that is retained when
#: the plan is scaled down to fit the budget.
COST_FLOOR_RATIO = 0.45


def _fit_to_budget(itinerary: Itinerary, preferences: TripPreferences) -> Itinerary:
    """Scale activity costs down so the total fits the user's budget."""
    budget = float(preferences.budget)
    current = sum(
        float(activity.estimated_cost or 0)
        for day in itinerary.days
        for activity in day.activities
    )

    if current <= budget or current <= 0:
        return itinerary

    # How much can we scale down before hitting the floor on every activity?
    floor_total = sum(
        float(activity.estimated_cost or 0) * COST_FLOOR_RATIO
        for day in itinerary.days
        for activity in day.activities
    )
    if floor_total >= budget:
        # Even a minimum viable trip exceeds the budget - report it honestly.
        return itinerary

    # Scale factor that brings the total to exactly the budget.
    factor = budget / current
    if factor < COST_FLOOR_RATIO:
        factor = COST_FLOOR_RATIO

    for day in itinerary.days:
        for activity in day.activities:
            original = float(activity.estimated_cost or 0)
            if original <= 0:
                continue
            scaled = round(max(original * COST_FLOOR_RATIO, original * factor), 2)
            activity.estimated_cost = scaled

    return itinerary
