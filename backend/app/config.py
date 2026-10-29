"""Application configuration loaded from environment variables / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from the backend root (never from the repository root).
load_dotenv(BASE_DIR / ".env", override=False)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Config:
    """Runtime configuration for the travel itinerary planner API.

    Every environment lookup happens in a ``default_factory`` so that the
    values are read when the config is instantiated, not when this module is
    first imported. That keeps the config testable and lets tests patch the
    environment at runtime.
    """

    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "dev-secret-key"))
    port: int = field(default_factory=lambda: _as_int(os.getenv("PORT"), 8000))
    debug: bool = field(default_factory=lambda: _as_bool(os.getenv("DEBUG"), False))

    gemini_api_key: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip()
    )
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
    )
    gemini_max_retries: int = field(
        default_factory=lambda: _as_int(os.getenv("GEMINI_MAX_RETRIES"), 2)
    )

    supabase_url: str = field(
        default_factory=lambda: os.getenv("SUPABASE_URL", "").strip()
    )
    supabase_key: str = field(
        default_factory=lambda: os.getenv("SUPABASE_KEY", "").strip()
    )
    supabase_jwt_secret: str = field(
        default_factory=lambda: os.getenv("SUPABASE_JWT_SECRET", "").strip()
    )
    supabase_trips_table: str = field(
        default_factory=lambda: os.getenv("SUPABASE_TRIPS_TABLE", "trips").strip()
    )

    local_db_path: str = field(
        default_factory=lambda: os.getenv("LOCAL_DB_PATH", "./data/trips.db").strip()
    )

    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,"
                "http://localhost:4173,http://127.0.0.1:4173",
            ).split(",")
            if origin.strip()
        )
    )

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------
    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def auth_enabled(self) -> bool:
        return bool(self.supabase_jwt_secret)

    @property
    def resolved_local_db_path(self) -> Path:
        path = Path(self.local_db_path)
        if not path.is_absolute():
            path = (BASE_DIR / path).resolve()
        return path

    def public_snapshot(self) -> dict:
        """Safe-to-expose view of the configuration (no secrets)."""
        return {
            "ai_provider": "gemini" if self.gemini_enabled else "template-fallback",
            "gemini_model": self.gemini_model if self.gemini_enabled else None,
            "storage_backend": "supabase" if self.supabase_enabled else "local-sqlite",
            "auth_required": self.auth_enabled,
        }


_config: Config | None = None


def get_config() -> Config:
    """Return the process-wide configuration singleton."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Drop the cached config (used by tests that patch environment values)."""
    global _config
    _config = None
