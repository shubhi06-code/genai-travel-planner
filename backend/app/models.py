"""Pydantic request/response schemas for the travel itinerary planner."""

from __future__ import annotations

from datetime import date, datetime, timezone
from datetime import date as DateType
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Limits enforced by the backend (the frontend mirrors these).
# ---------------------------------------------------------------------------
MAX_TRIP_DAYS = 14
MIN_TRIP_DAYS = 1
MAX_TRAVELERS = 20


class TravelStyle(str, Enum):
    RELAXED = "relaxed"
    BALANCED = "balanced"
    PACKED = "packed"
    ADVENTURE = "adventure"
    CULTURAL = "cultural"
    ROMANTIC = "romantic"
    FAMILY_FRIENDLY = "family-friendly"


class AccommodationPreference(str, Enum):
    HOSTEL = "hostel"
    BUDGET_HOTEL = "budget-hotel"
    MID_RANGE = "mid-range"
    BOUTIQUE = "boutique"
    LUXURY = "luxury"
    RESORT = "resort"
    GUESTHOUSE = "guesthouse"


class TransportationPreference(str, Enum):
    WALKING = "walking"
    PUBLIC_TRANSIT = "public-transit"
    TAXI_RIDESHARE = "taxi-rideshare"
    RENTAL_CAR = "rental-car"
    MIXED = "mixed"


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    TRY = "TRY"
    INR = "INR"
    AUD = "AUD"
    CAD = "CAD"
    JPY = "JPY"


#: Interests the backend accepts. The frontend renders this exact list.
INTERESTS: tuple[str, ...] = (
    "food",
    "sightseeing",
    "history",
    "culture",
    "art",
    "architecture",
    "nature",
    "hiking",
    "adventure",
    "beach",
    "nightlife",
    "shopping",
    "wellness",
    "museums",
    "photography",
    "local-experience",
    "family-friendly",
    "romantic",
    "wildlife",
)

#: Maximum number of interests accepted in a single request.
MAX_INTERESTS = 8


class TripPreferences(BaseModel):
    """Validated trip preferences submitted to the itinerary generator."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        validate_assignment=True,
    )

    destination: str = Field(
        ...,
        min_length=2,
        max_length=120,
        description="City, region or country to plan a trip for.",
    )
    start_date: date = Field(..., description="First day of the trip (YYYY-MM-DD).")
    end_date: date = Field(..., description="Last day of the trip (YYYY-MM-DD).")
    budget: float = Field(
        ...,
        gt=0,
        le=10_000_000,
        description="Total budget for the whole party in the selected currency.",
    )
    currency: Currency = Field(default=Currency.USD)
    travelers: int = Field(
        ...,
        ge=1,
        le=MAX_TRAVELERS,
        description="Number of people travelling.",
    )
    interests: list[str] = Field(
        default_factory=list,
        max_length=MAX_INTERESTS,
        description="Zero-based or descriptive interests driving the plan.",
    )
    travel_style: TravelStyle = Field(default=TravelStyle.BALANCED)
    accommodation: AccommodationPreference = Field(default=AccommodationPreference.MID_RANGE)
    transportation: TransportationPreference = Field(
        default=TransportationPreference.MIXED
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional free-text requests, e.g. 'dietary restrictions'.",
    )
    # A trip being edited may legitimately start in the past; new trips may not.
    allow_past_dates: bool = Field(
        default=False,
        exclude=True,
        description="Internal flag: true when editing an existing trip.",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("destination")
    @classmethod
    def _destination_not_blank(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Destination must not be empty.")
        if cleaned.isdigit():
            raise ValueError("Destination must be a place name.")
        return cleaned

    @field_validator("budget")
    @classmethod
    def _budget_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Budget must be a positive number.")
        return round(float(value), 2)

    @field_validator("travelers")
    @classmethod
    def _travelers_valid(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Traveler count must be a positive integer.")
        return int(value)

    @field_validator("interests")
    @classmethod
    def _normalise_interests(cls, value: list[str]) -> list[str]:
        seen: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("Each interest must be a string.")
            cleaned = item.strip().lower().replace("_", "-")
            if not cleaned:
                continue
            if cleaned not in seen:
                seen.append(cleaned)
        return seen

    @model_validator(mode="after")
    def _validate_date_range(self) -> "TripPreferences":
        if self.end_date < self.start_date:
            raise ValueError("End date must be the same as or later than the start date.")

        duration = (self.end_date - self.start_date).days + 1
        if duration < MIN_TRIP_DAYS:
            raise ValueError("Trip duration must be at least one day.")
        if duration > MAX_TRIP_DAYS:
            raise ValueError(
                f"Trip duration must be {MAX_TRIP_DAYS} days or fewer "
                f"(received {duration} days)."
            )

        if not self.allow_past_dates:
            today = datetime.now(timezone.utc).date()
            if self.start_date < today:
                raise ValueError("Start date must not be in the past for a new trip.")
        return self

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class Activity(BaseModel):
    """A single planned item inside a day."""

    model_config = ConfigDict(extra="ignore")

    name: str
    description: str = ""
    time: str = Field(default="", description="Suggested start time, e.g. '09:30'.")
    duration: str = Field(default="", description="Human readable duration, e.g. '1.5 h'.")
    location: str = ""
    category: Literal[
        "attraction",
        "food",
        "accommodation",
        "transport",
        "leisure",
        "shopping",
        "other",
    ] = "other"
    estimated_cost: float = Field(default=0.0, ge=0)
    cost_note: str = ""
    tip: str = ""
    transport_note: str = ""
    is_estimate: bool = True


class DayPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    day_number: int = Field(..., ge=1)
    date: DateType | None = None
    title: str = ""
    theme: str = ""
    summary: str = ""
    activities: list[Activity] = Field(default_factory=list)
    meals: dict[str, str] = Field(default_factory=dict)
    daily_estimated_cost: float = Field(default=0.0, ge=0)
    notes: str = ""


class BudgetBreakdown(BaseModel):
    model_config = ConfigDict(extra="ignore")

    accommodation: float = 0.0
    food: float = 0.0
    activities: float = 0.0
    transport: float = 0.0
    total: float = 0.0
    per_person: float = 0.0
    budget: float = 0.0
    remaining: float = 0.0
    over_budget: bool = False
    over_budget_amount: float = 0.0
    utilization_percent: float = 0.0
    currency: str = "USD"
    notes: list[str] = Field(default_factory=list)


class Itinerary(BaseModel):
    """The complete generated travel plan returned to the frontend."""

    model_config = ConfigDict(extra="ignore")

    title: str = ""
    summary: str = ""
    destination: str = ""
    start_date: DateType | None = None
    end_date: DateType | None = None
    duration_days: int = 1
    travelers: int = 1
    currency: str = "USD"
    days: list[DayPlan] = Field(default_factory=list)
    budget: BudgetBreakdown = Field(default_factory=BudgetBreakdown)
    travel_tips: list[str] = Field(default_factory=list)
    packing_list: list[str] = Field(default_factory=list)
    generated_by: str = "template-fallback"
    disclaimer: str = (
        "All costs, opening hours, transport schedules and availability are "
        "estimates and must be verified before travel."
    )


class GenerateItineraryResponse(BaseModel):
    itinerary: Itinerary
    preferences: TripPreferences
    meta: dict[str, Any] = Field(default_factory=dict)


class SaveTripRequest(BaseModel):
    """Body for POST /api/trips and PUT /api/trips/{trip_id}."""

    model_config = ConfigDict(extra="ignore")

    preferences: TripPreferences
    itinerary: Itinerary
    title: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class UpdateTripRequest(BaseModel):
    """Body for PUT /api/trips/{trip_id} - every field optional."""

    model_config = ConfigDict(extra="ignore")

    preferences: TripPreferences | None = None
    itinerary: Itinerary | None = None
    title: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class TripSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str = ""
    destination: str = ""
    start_date: DateType | None = None
    end_date: DateType | None = None
    travelers: int = 1
    budget: float = 0.0
    currency: str = "USD"
    total_estimated_cost: float = 0.0
    status: Literal["upcoming", "ongoing", "past"] = "upcoming"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Trip(TripSummary):
    preferences: TripPreferences | None = None
    itinerary: Itinerary | None = None
    notes: str | None = None
    owner_id: str | None = None


class DeleteTripResponse(BaseModel):
    id: str
    deleted: bool = True
    message: str = "Trip deleted."


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


BudgetAmount = Annotated[float, Field(ge=0)]
