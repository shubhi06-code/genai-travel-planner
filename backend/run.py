"""Development entrypoint.

Run with:

    python run.py

or with the Flask CLI:

    flask --app run:app run --debug
"""

from __future__ import annotations

import logging
import os

from app import create_app
from app.config import get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

app = create_app()


if __name__ == "__main__":
    config = get_config()
    snapshot = config.public_snapshot()
    print("=" * 68)
    print("  Travel Itinerary Planner API")
    print(f"  AI provider   : {snapshot['ai_provider']}")
    print(f"  Storage       : {snapshot['storage_backend']}")
    print(f"  Auth required : {snapshot['auth_required']}")
    print("=" * 68)

    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=config.port,
        debug=config.debug,
    )
