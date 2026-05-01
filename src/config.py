"""Runtime configuration for the service."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    scheduler_interval_seconds: int = 120
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_host=os.getenv("APP_HOST", cls.app_host),
            app_port=int(os.getenv("APP_PORT", str(cls.app_port))),
            scheduler_interval_seconds=int(
                os.getenv("SCHEDULER_INTERVAL_SECONDS", str(cls.scheduler_interval_seconds))
            ),
            log_level=os.getenv("LOG_LEVEL", cls.log_level).upper(),
        )
