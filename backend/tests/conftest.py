"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import reset_config  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure no real credentials leak into the test suite."""
    for var in (
        "GEMINI_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "SUPABASE_JWT_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)
    reset_config()
    yield
    reset_config()


@pytest.fixture
def tomorrow() -> date:
    return date.today() + timedelta(days=1)


@pytest.fixture
def sample_preferences(tomorrow: date) -> dict:
    return {
        "destination": "Lisbon, Portugal",
        "start_date": tomorrow.isoformat(),
        "end_date": (tomorrow + timedelta(days=2)).isoformat(),
        "budget": 900.0,
        "currency": "EUR",
        "travelers": 2,
        "interests": ["food", "sightseeing", "history"],
        "travel_style": "balanced",
        "accommodation": "mid-range",
        "transportation": "mixed",
    }


@pytest.fixture
def local_db_env(monkeypatch, tmp_path):
    """Force the storage layer into local SQLite mode inside a temp dir."""
    db_path = tmp_path / "test_trips.db"
    monkeypatch.setenv("LOCAL_DB_PATH", str(db_path))
    reset_config()
    yield db_path
    reset_config()


@pytest.fixture
def app(local_db_env):
    from app import create_app

    application = create_app({"TESTING": True})
    yield application


@pytest.fixture
def client(app):
    return app.test_client()
