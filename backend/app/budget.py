"""Budget estimation and budget-health checks."""

from __future__ import annotations

from typing import Iterable

from .models import BudgetBreakdown, Itinerary, TripPreferences

#: Share of the total budget that each category usually consumes. These are
#: used by the deterministic template generator, never as a claim about a
#: specific trip.
DEFAULT_SPLIT = {
    "accommodation": 0.42,
    "food": 0.22,
    "activities": 0.21,
    "transport": 0.15,
}

#: Nightly cost multipliers per accommodation preference (relative units).
ACCOMMODATION_NIGHTLY = {
    "hostel": 28.0,
    "guesthouse": 45.0,
    "budget-hotel": 65.0,
    "mid-range": 110.0,
    "boutique": 165.0,
    "luxury": 280.0,
    "resort": 320.0,
}

#: Daily transport cost per traveller, by transportation preference.
TRANSPORT_PER_DAY = {
    "walking": 4.0,
    "public-transit": 14.0,
    "taxi-rideshare": 28.0,
    "rental-car": 42.0,
    "mixed": 20.0,
}

#: Rough daily food spend per traveller, scaled by travel style.
FOOD_PER_DAY_BY_STYLE = {
    "relaxed": 38.0,
    "balanced": 32.0,
    "packed": 26.0,
    "adventure": 28.0,
    "cultural": 30.0,
    "romantic": 62.0,
    "family-friendly": 34.0,
}


def _round(value: float) -> float:
    return round(float(value), 2)


def calculate_budget(
    preferences: TripPreferences,
    accommodation: float = 0.0,
    food: float = 0.0,
    activities: float = 0.0,
    transport: float = 0.0,
    notes: Iterable[str] | None = None,
) -> BudgetBreakdown:
    """Build a :class:`BudgetBreakdown` from category estimates.

    The breakdown always reports the total, the per-person figure, how much of
    the user's budget remains (or by how much it is exceeded) and advisory
    notes when the plan is tight or over budget.
    """
    accommodation = max(0.0, float(accommodation))
    food = max(0.0, float(food))
    activities = max(0.0, float(activities))
    transport = max(0.0, float(transport))

    total = _round(accommodation + food + activities + transport)
    travelers = max(1, int(preferences.travelers))
    budget = _round(float(preferences.budget))

    per_person = _round(total / travelers)
    remaining = _round(budget - total)
    over_budget = total > budget
    over_by = _round(max(0.0, total - budget))
    utilization = _round((total / budget) * 100) if budget > 0 else 0.0

    note_list = list(notes or [])
    if over_budget:
        note_list.append(
            f"Estimated total exceeds the budget by {over_by:.2f} "
            f"{preferences.currency.value}. Reduce activities, upgrade the "
            f"accommodation tier or extend the trip to bring it in line."
        )
    elif utilization >= 90:
        note_list.append(
            f"The plan is tight: it uses {utilization:.0f}% of the budget and "
            f"leaves little room for unexpected expenses. A 10-15% contingency "
            f"is recommended."
        )
    if total == 0:
        note_list.append(
            "No cost estimates are available for this itinerary yet."
        )

    return BudgetBreakdown(
        accommodation=_round(accommodation),
        food=_round(food),
        activities=_round(activities),
        transport=_round(transport),
        total=total,
        per_person=per_person,
        budget=budget,
        remaining=remaining,
        over_budget=over_budget,
        over_budget_amount=over_by,
        utilization_percent=utilization,
        currency=preferences.currency.value,
        notes=note_list,
    )


def calculate_budget_from_itinerary(
    preferences: TripPreferences, itinerary: Itinerary
) -> dict[str, float]:
    """Sum the per-activity estimates of an itinerary by category."""
    totals = {"accommodation": 0.0, "food": 0.0, "activities": 0.0, "transport": 0.0}

    for day in itinerary.days:
        for activity in day.activities:
            cost = float(activity.estimated_cost or 0)
            if activity.category == "accommodation":
                totals["accommodation"] += cost
            elif activity.category == "food":
                totals["food"] += cost
            elif activity.category == "transport":
                totals["transport"] += cost
            elif activity.category in {"attraction", "shopping", "leisure"}:
                totals["activities"] += cost
            else:
                totals["activities"] += cost

    return {key: _round(value) for key, value in totals.items()}


def estimate_category_costs(preferences: TripPreferences) -> dict[str, float]:
    """Estimate category costs from the user's preferences alone.

    Used by the deterministic fallback generator and by the endpoint's
    ``/api/estimate-budget`` helper.
    """
    nights = max(0, preferences.duration_days - 1)
    travelers = max(1, preferences.travelers)
    days = preferences.duration_days

    nightly = ACCOMMODATION_NIGHTLY.get(preferences.accommodation.value, 110.0)
    accommodation = nightly * nights * travelers

    food = (
        FOOD_PER_DAY_BY_STYLE.get(preferences.travel_style.value, 32.0) * days * travelers
    )

    transport = (
        TRANSPORT_PER_DAY.get(preferences.transportation.value, 20.0) * days * travelers
    )

    budget = float(preferences.budget)
    activity_share = max(0.05, min(0.30, 1.0 - DEFAULT_SPLIT["accommodation"]))
    residual = max(0.0, budget - accommodation - food - transport)
    activities = residual * activity_share

    return {
        "accommodation": _round(accommodation),
        "food": _round(food),
        "activities": _round(activities),
        "transport": _round(transport),
    }
