"""Deterministic template itinerary generator.

Used when the Gemini API is unavailable or fails. It produces a realistic,
fully-structured plan that respects the traveller's pace, interests,
accommodation tier and budget, so the application is always usable.
"""

from __future__ import annotations

from datetime import timedelta

from .models import Activity, DayPlan, Itinerary, TripPreferences

#: Number of activities per day, keyed by travel style.
PACE_ACTIVITIES = {
    "relaxed": 4,
    "balanced": 5,
    "packed": 7,
    "adventure": 6,
    "cultural": 5,
    "romantic": 5,
    "family-friendly": 5,
}

#: Interest -> (activity name, description) used for the daily spotlight.
INTEREST_SPOTLIGHTS: dict[str, tuple[str, str]] = {
    "food": (
        "Old town food walk",
        "A guided tasting walk through the historic market district, stopping at "
        "regional stalls and a family-run tavern for the classic local dishes.",
    ),
    "sightseeing": (
        "Signature city landmarks",
        "A self-guided route through the most iconic viewpoints and historic "
        "landmarks, with time to photograph the best panoramas.",
    ),
    "history": (
        "Heritage and old town trail",
        "A walking route through the historic quarter covering the founding "
        "chambers, the old walls and the sites that shaped the city.",
    ),
    "culture": (
        "Local culture and workshop visit",
        "An afternoon with local artisans, covering a traditional craft workshop "
        "and the neighbourhood's cultural institutions.",
    ),
    "art": (
        "Contemporary art galleries",
        "A curated visit to the city's key galleries and public art installations, "
        "including a sculpture garden and a contemporary museum.",
    ),
    "architecture": (
        "Architectural highlights walk",
        "A route through the city's signature buildings, from grand civic "
        "architecture to the modernist landmarks on the waterfront.",
    ),
    "nature": (
        "Botanical gardens and green spaces",
        "A slow walk through the botanical gardens and the riverside parks, "
        "with time for a coffee on the lawns.",
    ),
    "hiking": (
        "Ridge and trail hike",
        "A guided ridge walk with a panoramic viewpoint, moderate difficulty, "
        "with the option to shorten the route.",
    ),
    "adventure": (
        "Active adventure session",
        "An active morning combining a guided outdoor session with a local "
        "operator, suitable for the whole group.",
    ),
    "beach": (
        "Coastal beach morning",
        "A relaxed morning on the closest accessible beach, with time for "
        "swimming and a promenade lunch.",
    ),
    "nightlife": (
        "Evening bar and live music scene",
        "An evening in the neighbourhood's best-known bars and small live "
        "music venues, with a late dinner in between.",
    ),
    "shopping": (
        "Independent shops and local market",
        "A browse through the independent design shops, artisan studios and "
        "the covered market stalls.",
    ),
    "wellness": (
        "Spa and wellness morning",
        "A restorative morning at a well-reviewed day spa, with a hammam, "
        "massage or thermal circuit depending on availability.",
    ),
    "museums": (
        "Museum and gallery highlights",
        "A focused museum route covering the city's most important permanent "
        "collections, with a highlights gallery and the archaeological museum.",
    ),
    "photography": (
        "Golden hour photography walk",
        "A guided photography walk timed for the best light of the day, "
        "covering classic vantage points and quieter side streets.",
    ),
    "local-experience": (
        "Neighbourhood local experience",
        "A real neighbourhood afternoon - a small market, a community square "
        "and a chat with residents about how the city actually lives.",
    ),
    "family-friendly": (
        "Family friendly attractions",
        "A low-stress day of child-friendly attractions, interactive museums "
        "and plenty of breaks in shaded park areas.",
    ),
    "romantic": (
        "Romantic viewpoints and dinner",
        "A sunset viewpoint, a slow walk along the water and a reserved table "
        "at a candlelit restaurant nearby.",
    ),
    "wildlife": (
        "Nature reserve and wildlife walk",
        "A guided visit to the regional nature reserve with a naturalist, "
        "covering local species and the short walking trails.",
    ),
}

#: Extra activity templates, used to fill out a day to the requested pace.
EXTRA_ACTIVITIES: list[tuple[str, str, str, str]] = [
    (
        "Neighbourhood viewpoint",
        "A short climb to the best-known viewpoint in the area, with time for "
        "photos and a pause in the shade.",
        "leisure",
        "1 h",
    ),
    (
        "Independent gallery visit",
        "A relaxed browse through a smaller independent gallery or design shop "
        "with rotating local exhibitions.",
        "attraction",
        "1.5 h",
    ),
    (
        "Riverside or waterfront stroll",
        "An unhurried walk along the waterfront with benches and coffee stops "
        "along the way.",
        "leisure",
        "1 h",
    ),
    (
        "Historic cafe stop",
        "A break in a long-established cafe in a historic building - a reliable "
        "place to rest and people-watch.",
        "food",
        "45 min",
    ),
    (
        "Local market browsing",
        "A slow pass through the neighbourhood market, the best place for "
        "regional produce, street food and picnic supplies.",
        "shopping",
        "1 h",
    ),
    (
        "Museum annex visit",
        "A smaller museum or exhibition annex for a focused, quiet hour away "
        "from the main crowds.",
        "attraction",
        "1.5 h",
    ),
    (
        "Park and garden rest",
        "A shaded break in the city gardens, with time for a picnic or an "
        "ice cream if the weather is warm.",
        "leisure",
        "1 h",
    ),
]

#: Accommodation tier -> nightly cost per traveller, in the trip currency.
NIGHTLY_COST = {
    "hostel": 28.0,
    "guesthouse": 45.0,
    "budget-hotel": 65.0,
    "mid-range": 110.0,
    "boutique": 165.0,
    "luxury": 280.0,
    "resort": 320.0,
}

#: Meal cost per traveller, by travel style.
MEAL_COST = {
    "relaxed": 42.0,
    "balanced": 34.0,
    "packed": 27.0,
    "adventure": 30.0,
    "cultural": 33.0,
    "romantic": 68.0,
    "family-friendly": 36.0,
}

#: Activity entry cost per traveller.
ACTIVITY_COST = {
    "relaxed": 26.0,
    "balanced": 32.0,
    "packed": 40.0,
    "adventure": 44.0,
    "cultural": 34.0,
    "romantic": 42.0,
    "family-friendly": 30.0,
}


def _spotlight_for(interests: list[str]) -> tuple[str, str]:
    """Pick the activity matching the traveller's strongest interest."""
    for interest in interests:
        if interest in INTEREST_SPOTLIGHTS:
            return INTEREST_SPOTLIGHTS[interest]
    return INTEREST_SPOTLIGHTS["sightseeing"]


def _spotlight_for_day(interests: list[str], day_index: int) -> tuple[str, str]:
    """Pick a spotlight activity that rotates through the traveller's interests.

    Rotating means each day leads with something different instead of every
    day repeating the same opening activity.
    """
    if not interests:
        return INTEREST_SPOTLIGHTS["sightseeing"]

    usable = [i for i in interests if i in INTEREST_SPOTLIGHTS]
    if not usable:
        return INTEREST_SPOTLIGHTS["sightseeing"]

    # Start at the first interest, then rotate through the list.
    chosen = usable[day_index % len(usable)]
    return INTEREST_SPOTLIGHTS[chosen]


def _meal_cost(preferences: TripPreferences) -> float:
    return MEAL_COST.get(preferences.travel_style.value, 34.0)


def _activity_cost(preferences: TripPreferences) -> float:
    return ACTIVITY_COST.get(preferences.travel_style.value, 32.0)


def _transport_cost(preferences: TripPreferences) -> float:
    per_day = {
        "walking": 3.0,
        "public-transit": 12.0,
        "taxi-rideshare": 26.0,
        "rental-car": 44.0,
        "mixed": 18.0,
    }
    return per_day.get(preferences.transportation.value, 18.0)


def _food_choices(destination: str, style: str) -> dict[str, str]:
    if style == "romantic":
        return {
            "breakfast": "Breakfast at a terrace cafe in the old quarter",
            "lunch": "Lunch at a small bistro near the main sights",
            "dinner": "Candlelit dinner in the historic dining district",
        }
    if style in {"packed", "adventure"}:
        return {
            "breakfast": "Quick breakfast at a bakery near your accommodation",
            "lunch": "Casual lunch at a market hall counter",
            "dinner": "Early dinner at a busy local tavern",
        }
    return {
        "breakfast": "Breakfast at a neighbourhood cafe",
        "lunch": "Lunch at a locally loved spot near the afternoon sights",
        "dinner": "Dinner in the city's restaurant district",
    }


def build_template_itinerary(preferences: TripPreferences) -> Itinerary:
    """Build a deterministic, fully-formed itinerary from the preferences."""
    destination = preferences.destination
    days_count = preferences.duration_days
    target_activities = PACE_ACTIVITIES.get(preferences.travel_style.value, 5)
    travelers = max(1, preferences.travelers)
    style = preferences.travel_style.value

    activity_cost = round(_activity_cost(preferences) * travelers, 2)
    meal_cost = round(_meal_cost(preferences) * travelers, 2)
    transport_cost = round(_transport_cost(preferences) * travelers, 2)
    nightly_cost = round(
        NIGHTLY_COST.get(preferences.accommodation.value, 110.0) * travelers, 2
    )

    days: list[DayPlan] = []

    for day_index in range(days_count):
        day_date = preferences.start_date + timedelta(days=day_index)
        day_number = day_index + 1
        is_last = day_index == days_count - 1

        activities: list[Activity] = []

        # 1. Daily spotlight driven by the traveller's interests (rotated so
        #    each day leads with something different).
        spot_name, spot_desc = _spotlight_for_day(preferences.interests, day_index)
        activities.append(
            Activity(
                name=spot_name,
                description=spot_desc,
                time="09:30",
                duration="2 h",
                location=f"{destination} - city centre",
                category="attraction",
                estimated_cost=activity_cost,
                cost_note="Estimated entry / guide fee for the group.",
                tip="Start early to get the quieter light and fewer queues.",
                transport_note="Walk or short metro ride from the accommodation.",
            )
        )

        # 2. Transport between activities.
        activities.append(
            Activity(
                name="Transfer to the next district",
                description=(
                    "Move across town using the option that best matches the "
                    f"{preferences.transportation.value} preference."
                ),
                time="11:45",
                duration="30 min",
                location=f"{destination} - transit",
                category="transport",
                estimated_cost=transport_cost,
                cost_note="Estimated local transport spend for the day.",
                transport_note="Check live timetables before setting out.",
            )
        )

        # 3. Lunch.
        activities.append(
            Activity(
                name="Lunch",
                description="A relaxed lunch stop in the neighbourhood of the "
                "morning activity.",
                time="12:30",
                duration="1 h 15 min",
                location=f"{destination} - local dining street",
                category="food",
                estimated_cost=round(meal_cost * 0.75, 2),
                cost_note="Estimated for the group.",
                tip="Ask for the daily specials to keep the cost down.",
            )
        )

        # 4+ Fill the day out to the requested pace. The rotation is offset by
        #    the day so consecutive days do not reuse the same fillers.
        extras_needed = max(0, target_activities - len(activities))
        for extra_index in range(extras_needed):
            offset = day_index * extras_needed + extra_index
            template = EXTRA_ACTIVITIES[offset % len(EXTRA_ACTIVITIES)]
            name, description, category, duration = template
            activities.append(
                Activity(
                    name=name,
                    description=description,
                    time="15:00" if extra_index % 2 == 0 else "17:30",
                    duration=duration,
                    location=f"{destination}",
                    category=category,  # type: ignore[arg-type]
                    estimated_cost=round(activity_cost * 0.6, 2)
                    if category != "food"
                    else round(meal_cost * 0.4, 2),
                    cost_note="Estimated cost, may vary by season.",
                    tip="Flexible slot - drop it if the day runs long.",
                )
            )

        # Dinner.
        activities.append(
            Activity(
                name="Dinner",
                description="An evening meal in the area's best dining streets.",
                time="19:30",
                duration="1 h 30 min",
                location=f"{destination} - restaurant district",
                category="food",
                estimated_cost=round(meal_cost * 0.85, 2),
                cost_note="Estimated for the group.",
            )
        )

        meals = _food_choices(destination, style)
        if is_last:
            meals["dinner"] = "Farewell dinner on the final evening"

        # Accommodation entry on the first night only.
        if day_index == 0:
            activities.insert(
                0,
                Activity(
                    name="Check in and settle in",
                    description=(
                        f"Arrive at your {preferences.accommodation.value} "
                        "accommodation, drop your bags and orient yourself."
                    ),
                    time="15:00",
                    duration="1 h",
                    location=f"{destination} - accommodation",
                    category="accommodation",
                    estimated_cost=nightly_cost,
                    cost_note="Estimated for the first night.",
                    tip="Confirm the check-in window before you travel.",
                ),
            )

        day_title = _day_title(day_number, days_count, preferences.interests)
        days.append(
            DayPlan(
                day_number=day_number,
                date=day_date,
                title=day_title,
                theme=_day_theme(preferences.interests, day_number),
                summary=_day_summary(destination, day_number, preferences),
                activities=activities,
                meals=meals,
                notes=(
                    "Confirm opening hours and reservations before travelling."
                    if day_number == 1
                    else "Keep the evening flexible for spontaneous finds."
                ),
            )
        )

    tips = [
        f"Keep a copy of your bookings for {destination} offline.",
        "Opening hours, transport timetables and prices change - verify them "
        "before travelling.",
        "Carry some local cash for small shops and market stalls.",
        "Ask locally about seasonal closures; many sights close on one weekday.",
    ]
    if preferences.travelers > 2:
        tips.append(
            "For a group this size, book tables and tickets together to keep "
            "everyone together."
        )
    if preferences.travel_style.value == "packed":
        tips.append(
            "This is a dense schedule - leave one afternoon flexible in case "
            "you need to slow down."
        )

    packing = [
        "Comfortable walking shoes",
        "Comfortable walking shoes",
        "Portable charger",
        "Refillable water bottle",
        "Light day bag",
        "Sunscreen and hat",
    ]
    packing = list(dict.fromkeys(packing))

    return Itinerary(
        title=f"{days_count} day{'s' if days_count != 1 else ''} in {destination}",
        summary=(
            f"A {preferences.travel_style.value} {days_count}-day plan for "
            f"{preferences.travelers} traveller{'s' if preferences.travelers != 1 else ''} "
            f"in {destination}, built around "
            f"{', '.join(preferences.interests) if preferences.interests else 'general sightseeing'}. "
            f"The plan groups nearby sights together to reduce travel time and "
            f"keeps the estimated spend within the set budget."
        ),
        destination=destination,
        start_date=preferences.start_date,
        end_date=preferences.end_date,
        duration_days=days_count,
        travelers=preferences.travelers,
        currency=preferences.currency.value,
        days=days,
        travel_tips=tips,
        packing_list=packing,
        generated_by="template-fallback",
    )


def _day_title(day_number: int, total_days: int, interests: list[str]) -> str:
    """Build a day title that always reflects that day's focus."""
    focus = ""
    if interests:
        usable = [i for i in interests if i in INTEREST_SPOTLIGHTS]
        if usable:
            focus = usable[(day_number - 1) % len(usable)].replace("-", " ").capitalize()
    if not focus:
        focus = "the highlights"

    if total_days == 1:
        return f"{focus} and the highlights of the day"
    if day_number == 1:
        return f"Arrival and {focus.lower()} on your first day"
    if day_number == total_days:
        return f"Last look: {focus.lower()} and the highlights"

    return f"{focus} and the highlights of the day"


def _day_theme(interests: list[str], day_number: int) -> str:
    if not interests:
        return "Classic highlights"
    usable = [i for i in interests if i in INTEREST_SPOTLIGHTS]
    if not usable:
        return "Classic highlights"
    index = (day_number - 1) % len(usable)
    return usable[index].replace("-", " ").capitalize()


def _day_summary(destination: str, day_number: int, preferences: TripPreferences) -> str:
    focus = (
        preferences.interests[(day_number - 1) % len(preferences.interests)].replace("-", " ")
        if preferences.interests
        else "the main highlights"
    )
    return (
        f"A {preferences.travel_style.value} day in {destination} built around "
        f"{focus}. Nearby sights are grouped together to cut travel time, with "
        f"a proper meal break and room left for spontaneous finds."
    )
