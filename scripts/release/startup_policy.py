"""Bound portable readiness waiting by the configured worker preparation budget."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings


PROCESS_STARTUP_GRACE_SECONDS = 30.0


def startup_timeout_seconds(settings: Settings) -> float:
    """Use validated settings for the portable PostgreSQL interactive worker."""
    prewarm_seconds = (
        settings.worker_prewarm_timeout_seconds
        if settings.worker_prewarm_retrieval_cache
        and settings.chat_retrieval_cache
        and settings.database_url.startswith("postgresql")
        else 0.0
    )
    return PROCESS_STARTUP_GRACE_SECONDS + prewarm_seconds


def main() -> int:
    try:
        from app.core.config import Settings

        seconds = startup_timeout_seconds(Settings())
    except Exception as error:
        # Validation errors can contain private environment values.
        print(
            f"Startup readiness policy failed ({type(error).__name__}).",
            file=sys.stderr,
        )
        return 1
    print(seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
