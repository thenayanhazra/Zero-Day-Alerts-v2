"""Runtime configuration for the service."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    scheduler_interval_seconds: int = 120
    log_level: str = "INFO"
    alert_sink_timeout_seconds: float = 5.0
    alert_sink_retry_count: int = 1
    alert_sink_email_enabled: bool = True
    alert_sink_slack_enabled: bool = True
    alert_sink_webhook_enabled: bool = True
    alert_sink_email_min_severity: str = "medium"
    alert_sink_slack_min_severity: str = "high"
    alert_sink_webhook_min_severity: str = "low"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_host=os.getenv("APP_HOST", cls.app_host),
            app_port=int(os.getenv("APP_PORT", str(cls.app_port))),
            scheduler_interval_seconds=int(
                os.getenv("SCHEDULER_INTERVAL_SECONDS", str(cls.scheduler_interval_seconds))
            ),
            log_level=os.getenv("LOG_LEVEL", cls.log_level).upper(),
            alert_sink_timeout_seconds=float(
                os.getenv("ALERT_SINK_TIMEOUT_SECONDS", str(cls.alert_sink_timeout_seconds))
            ),
            alert_sink_retry_count=int(os.getenv("ALERT_SINK_RETRY_COUNT", str(cls.alert_sink_retry_count))),
            alert_sink_email_enabled=_as_bool(
                os.getenv("ALERT_SINK_EMAIL_ENABLED"),
                default=cls.alert_sink_email_enabled,
            ),
            alert_sink_slack_enabled=_as_bool(
                os.getenv("ALERT_SINK_SLACK_ENABLED"),
                default=cls.alert_sink_slack_enabled,
            ),
            alert_sink_webhook_enabled=_as_bool(
                os.getenv("ALERT_SINK_WEBHOOK_ENABLED"),
                default=cls.alert_sink_webhook_enabled,
            ),
            alert_sink_email_min_severity=os.getenv(
                "ALERT_SINK_EMAIL_MIN_SEVERITY", cls.alert_sink_email_min_severity
            ).lower(),
            alert_sink_slack_min_severity=os.getenv(
                "ALERT_SINK_SLACK_MIN_SEVERITY", cls.alert_sink_slack_min_severity
            ).lower(),
            alert_sink_webhook_min_severity=os.getenv(
                "ALERT_SINK_WEBHOOK_MIN_SEVERITY", cls.alert_sink_webhook_min_severity
            ).lower(),
        )
