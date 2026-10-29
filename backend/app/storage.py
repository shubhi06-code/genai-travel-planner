"""Trip persistence.

Two interchangeable backends are provided behind a single interface:

* :class:`SupabaseTripStore` - the production backend, backed by the Supabase
  Python SDK (see ``supabase/schema.sql`` for the table definition).
* :class:`LocalTripStore` - a SQLite backend used automatically when Supabase
  credentials are not configured, so the application is usable out of the box.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .errors import DatabaseError
from .models import Itinerary, Trip, TripPreferences, TripSummary

# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------


class TripStoreError(Exception):
    """Raised when the storage backend cannot fulfil a request."""


class TripStore(Protocol):
    """The contract every trip store implements."""

    def save(
        self,
        preferences: TripPreferences,
        itinerary: Itinerary,
        title: str | None = None,
        notes: str | None = None,
        owner_id: str | None = None,
    ) -> Trip: ...

    def list(self, owner_id: str | None = None) -> list[TripSummary]: ...

    def get(self, trip_id: str, owner_id: str | None = None) -> Trip | None: ...

    def update(
        self,
        trip_id: str,
        preferences: TripPreferences | None = None,
        itinerary: Itinerary | None = None,
        title: str | None = None,
        notes: str | None = None,
        owner_id: str | None = None,
    ) -> Trip: ...

    def delete(self, trip_id: str, owner_id: str | None = None) -> bool: ...


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def compute_status(start_date: date | None, end_date: date | None) -> str:
    """Return ``upcoming``, ``ongoing`` or ``past`` for the given dates."""
    if start_date is None or end_date is None:
        return "upcoming"
    today = date.today()
    if today > end_date:
        return "past"
    if today < start_date:
        return "upcoming"
    return "ongoing"


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


# ---------------------------------------------------------------------------
# Local SQLite backend
# ---------------------------------------------------------------------------

_CREATE_TABLE = """
create table if not exists trips (
    id                  text primary key,
    owner_id            text,
    title               text not null default '',
    destination         text not null,
    start_date          text,
    end_date            text,
    travelers           integer not null default 1,
    budget              real not null default 0,
    currency            text not null default 'USD',
    total_estimated_cost real not null default 0,
    status              text not null default 'upcoming',
    interests           text not null default '[]',
    travel_style        text,
    accommodation       text,
    transportation      text,
    notes               text,
    preferences_json    text not null default '{}',
    itinerary_json      text not null default '{}',
    created_at          text not null,
    updated_at          text not null
);
"""


class LocalTripStore:
    """SQLite-backed store used for local development and tests."""

    def __init__(self, local_db_path: str | Path):
        self.path = Path(local_db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    # -- internals --------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialise(self) -> None:
        try:
            with self._connect() as conn:
                conn.execute(_CREATE_TABLE)
        except sqlite3.Error as exc:  # pragma: no cover - defensive
            raise DatabaseError(f"Could not initialise local database: {exc}") from exc

    def _row_to_trip(self, row: sqlite3.Row) -> Trip:
        preferences_data = json.loads(row["preferences_json"] or "{}")
        itinerary_data = json.loads(row["itinerary_json"] or "{}")

        preferences = None
        if preferences_data:
            try:
                preferences = TripPreferences.model_validate(preferences_data)
            except Exception:  # pragma: no cover - tolerate older payloads
                preferences = None

        itinerary = Itinerary.model_validate(itinerary_data) if itinerary_data else None

        return Trip(
            id=row["id"],
            title=row["title"] or "",
            destination=row["destination"],
            start_date=_parse_date(row["start_date"]),
            end_date=_parse_date(row["end_date"]),
            travelers=row["travelers"],
            budget=row["budget"],
            currency=row["currency"],
            total_estimated_cost=row["total_estimated_cost"],
            status=row["status"],
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
            preferences=preferences,
            itinerary=itinerary,
            notes=row["notes"],
            owner_id=row["owner_id"],
        )

    # -- public API -------------------------------------------------------
    def save(
        self,
        preferences: TripPreferences,
        itinerary: Itinerary,
        title: str | None = None,
        notes: str | None = None,
        owner_id: str | None = None,
    ) -> Trip:
        trip_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        resolved_title = title or itinerary.title or f"Trip to {preferences.destination}"

        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    insert into trips (
                        id, owner_id, title, destination, start_date, end_date,
                        travelers, budget, currency, total_estimated_cost, status,
                        interests, travel_style, accommodation, transportation,
                        notes, preferences_json, itinerary_json, created_at, updated_at
                    ) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        trip_id,
                        owner_id,
                        resolved_title,
                        preferences.destination,
                        preferences.start_date.isoformat(),
                        preferences.end_date.isoformat(),
                        preferences.travelers,
                        preferences.budget,
                        preferences.currency.value,
                        itinerary.budget.total,
                        compute_status(preferences.start_date, preferences.end_date),
                        json.dumps(preferences.interests),
                        preferences.travel_style.value,
                        preferences.accommodation.value,
                        preferences.transportation.value,
                        notes,
                        json.dumps(preferences.model_dump(mode="json")),
                        json.dumps(itinerary.model_dump(mode="json")),
                        now,
                        now,
                    ),
                )
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not save trip: {exc}") from exc

        saved = self.get(trip_id)
        if saved is None:  # pragma: no cover - defensive
            raise DatabaseError("Trip was saved but could not be read back.")
        return saved

    def list(self, owner_id: str | None = None) -> list[TripSummary]:
        query = "select * from trips"
        params: list[Any] = []
        if owner_id is not None:
            query += " where owner_id = ?"
            params.append(owner_id)
        query += " order by created_at desc"

        try:
            with self._connect() as conn:
                rows = conn.execute(query, params).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not list trips: {exc}") from exc

        summaries: list[TripSummary] = []
        for row in rows:
            trip = self._row_to_trip(row)
            summaries.append(
                TripSummary(
                    id=trip.id,
                    title=trip.title,
                    destination=trip.destination,
                    start_date=trip.start_date,
                    end_date=trip.end_date,
                    travelers=trip.travelers,
                    budget=trip.budget,
                    currency=trip.currency,
                    total_estimated_cost=trip.total_estimated_cost,
                    status=trip.status,
                    created_at=trip.created_at,
                    updated_at=trip.updated_at,
                )
            )
        return summaries

    def get(self, trip_id: str, owner_id: str | None = None) -> Trip | None:
        query = "select * from trips where id = ?"
        params: list[Any] = [trip_id]
        if owner_id is not None:
            query += " and owner_id = ?"
            params.append(owner_id)

        try:
            with self._connect() as conn:
                row = conn.execute(query, params).fetchone()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not load trip: {exc}") from exc

        return self._row_to_trip(row) if row else None

    def update(
        self,
        trip_id: str,
        preferences: TripPreferences | None = None,
        itinerary: Itinerary | None = None,
        title: str | None = None,
        notes: str | None = None,
        owner_id: str | None = None,
    ) -> Trip:
        existing = self.get(trip_id, owner_id=owner_id)
        if existing is None:
            raise TripStoreError(f"Trip {trip_id} was not found.")

        resolved_prefs = preferences or existing.preferences
        resolved_itinerary = itinerary or existing.itinerary
        resolved_title = title if title is not None else existing.title
        resolved_notes = notes if notes is not None else existing.notes

        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    update trips set
                        title = ?, notes = ?, destination = ?, start_date = ?, end_date = ?,
                        travelers = ?, budget = ?, currency = ?, total_estimated_cost = ?,
                        status = ?, interests = ?, travel_style = ?, accommodation = ?,
                        transportation = ?, preferences_json = ?, itinerary_json = ?,
                        updated_at = ?
                    where id = ?
                    """,
                    (
                        resolved_title,
                        resolved_notes,
                        resolved_prefs.destination,
                        resolved_prefs.start_date.isoformat(),
                        resolved_prefs.end_date.isoformat(),
                        resolved_prefs.travelers,
                        resolved_prefs.budget,
                        resolved_prefs.currency.value,
                        resolved_itinerary.budget.total
                        if resolved_itinerary
                        else existing.total_estimated_cost,
                        compute_status(resolved_prefs.start_date, resolved_prefs.end_date),
                        json.dumps(resolved_prefs.interests),
                        resolved_prefs.travel_style.value,
                        resolved_prefs.accommodation.value,
                        resolved_prefs.transportation.value,
                        json.dumps(resolved_prefs.model_dump(mode="json")),
                        json.dumps(resolved_itinerary.model_dump(mode="json"))
                        if resolved_itinerary
                        else "{}",
                        datetime.now(timezone.utc).isoformat(),
                        trip_id,
                    ),
                )
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not update trip: {exc}") from exc

        updated = self.get(trip_id)
        if updated is None:  # pragma: no cover - defensive
            raise TripStoreError(f"Trip {trip_id} was not found after update.")
        return updated

    def delete(self, trip_id: str, owner_id: str | None = None) -> bool:
        existing = self.get(trip_id, owner_id=owner_id)
        if existing is None:
            return False
        try:
            with self._connect() as conn:
                conn.execute("delete from trips where id = ?", (trip_id,))
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not delete trip: {exc}") from exc
        return True


# ---------------------------------------------------------------------------
# Supabase backend
# ---------------------------------------------------------------------------


class SupabaseTripStore:
    """Store backed by the Supabase Python SDK."""

    def __init__(self, url: str, key: str, table: str = "trips"):
        try:
            from supabase import create_client
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise DatabaseError(
                "The supabase package is not installed. Run: pip install -r requirements.txt"
            ) from exc

        self.table = table
        try:
            self.client = create_client(url, key)
        except Exception as exc:
            raise DatabaseError(f"Could not connect to Supabase: {exc}") from exc

    # -- helpers ----------------------------------------------------------
    def _base_row(
        self,
        preferences: TripPreferences,
        itinerary: Itinerary,
        title: str,
        notes: str | None,
    ) -> dict[str, Any]:
        return {
            "title": title,
            "destination": preferences.destination,
            "start_date": preferences.start_date.isoformat(),
            "end_date": preferences.end_date.isoformat(),
            "travelers": preferences.travelers,
            "budget": float(preferences.budget),
            "currency": preferences.currency.value,
            "total_estimated_cost": float(itinerary.budget.total),
            "status": compute_status(preferences.start_date, preferences.end_date),
            "interests": preferences.interests,
            "travel_style": preferences.travel_style.value,
            "accommodation": preferences.accommodation.value,
            "transportation": preferences.transportation.value,
            "notes": notes,
            "preferences": preferences.model_dump(mode="json"),
            "itinerary": itinerary.model_dump(mode="json"),
        }

    @staticmethod
    def _row_to_trip(row: dict[str, Any]) -> Trip:
        preferences = None
        if row.get("preferences"):
            try:
                preferences = TripPreferences.model_validate(row["preferences"])
            except Exception:  # pragma: no cover - tolerate legacy payloads
                preferences = None

        itinerary = None
        if row.get("itinerary"):
            try:
                itinerary = Itinerary.model_validate(row["itinerary"])
            except Exception:  # pragma: no cover - tolerate legacy payloads
                itinerary = None

        return Trip(
            id=str(row.get("id")),
            title=row.get("title") or "",
            destination=row.get("destination") or "",
            start_date=_parse_date(row.get("start_date")),
            end_date=_parse_date(row.get("end_date")),
            travelers=int(row.get("travelers") or 1),
            budget=float(row.get("budget") or 0),
            currency=row.get("currency") or "USD",
            total_estimated_cost=float(row.get("total_estimated_cost") or 0),
            status=row.get("status") or "upcoming",
            created_at=_parse_datetime(row.get("created_at")),
            updated_at=_parse_datetime(row.get("updated_at")),
            preferences=preferences,
            itinerary=itinerary,
            notes=row.get("notes"),
            owner_id=row.get("user_id"),
        )

    # -- public API -------------------------------------------------------
    def save(
        self,
        preferences: TripPreferences,
        itinerary: Itinerary,
        title: str | None = None,
        notes: str | None = None,
        owner_id: str | None = None,
    ) -> Trip:
        resolved_title = title or itinerary.title or f"Trip to {preferences.destination}"
        payload = self._base_row(preferences, itinerary, resolved_title, notes)
        if owner_id:
            payload["user_id"] = owner_id

        try:
            response = self.client.table(self.table).insert(payload).execute()
        except Exception as exc:
            raise DatabaseError(f"Could not save trip to Supabase: {exc}") from exc

        rows = getattr(response, "data", None) or []
        if not rows:
            raise DatabaseError("Supabase did not return the inserted trip.")
        return self._row_to_trip(rows[0])

    def list(self, owner_id: str | None = None) -> list[TripSummary]:
        query = self.client.table(self.table).select("*").order("created_at", desc=True)
        if owner_id is not None:
            query = query.eq("user_id", owner_id)

        try:
            response = query.execute()
        except Exception as exc:
            raise DatabaseError(f"Could not list trips from Supabase: {exc}") from exc

        return [
            TripSummary(
                id=str(row.get("id")),
                title=row.get("title") or "",
                destination=row.get("destination") or "",
                start_date=_parse_date(row.get("start_date")),
                end_date=_parse_date(row.get("end_date")),
                travelers=int(row.get("travelers") or 1),
                budget=float(row.get("budget") or 0),
                currency=row.get("currency") or "USD",
                total_estimated_cost=float(row.get("total_estimated_cost") or 0),
                status=row.get("status") or "upcoming",
                created_at=_parse_datetime(row.get("created_at")),
                updated_at=_parse_datetime(row.get("updated_at")),
            )
            for row in (getattr(response, "data", None) or [])
        ]

    def get(self, trip_id: str, owner_id: str | None = None) -> Trip | None:
        query = self.client.table(self.table).select("*").eq("id", trip_id)
        if owner_id is not None:
            query = query.eq("user_id", owner_id)

        try:
            response = query.limit(1).execute()
        except Exception as exc:
            raise DatabaseError(f"Could not load trip from Supabase: {exc}") from exc

        rows = getattr(response, "data", None) or []
        return self._row_to_trip(rows[0]) if rows else None

    def update(
        self,
        trip_id: str,
        preferences: TripPreferences | None = None,
        itinerary: Itinerary | None = None,
        title: str | None = None,
        notes: str | None = None,
        owner_id: str | None = None,
    ) -> Trip:
        existing = self.get(trip_id, owner_id=owner_id)
        if existing is None:
            raise TripStoreError(f"Trip {trip_id} was not found.")

        resolved_prefs = preferences or existing.preferences
        if resolved_prefs is None:
            raise TripStoreError(f"Trip {trip_id} has no stored preferences.")

        resolved_itinerary = itinerary or existing.itinerary
        if resolved_itinerary is None:
            resolved_itinerary = Itinerary(destination=resolved_prefs.destination)

        payload = self._base_row(
            resolved_prefs,
            resolved_itinerary,
            title if title is not None else existing.title,
            notes if notes is not None else existing.notes,
        )
        if owner_id:
            payload["user_id"] = owner_id

        try:
            response = (
                self.client.table(self.table).update(payload).eq("id", trip_id).execute()
            )
        except Exception as exc:
            raise DatabaseError(f"Could not update trip in Supabase: {exc}") from exc

        rows = getattr(response, "data", None) or []
        if not rows:
            raise TripStoreError(f"Trip {trip_id} was not found.")
        return self._row_to_trip(rows[0])

    def delete(self, trip_id: str, owner_id: str | None = None) -> bool:
        existing = self.get(trip_id, owner_id=owner_id)
        if existing is None:
            return False

        query = self.client.table(self.table).delete().eq("id", trip_id)
        if owner_id is not None:
            query = query.eq("user_id", owner_id)

        try:
            query.execute()
        except Exception as exc:
            raise DatabaseError(f"Could not delete trip from Supabase: {exc}") from exc
        return True


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
