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
    enable_github_collector: bool = True
    enable_osint_feed_collector: bool = True
    enable_rss_forum_collector: bool = True
    enable_x_collector: bool = False
    github_token: str | None = None
    x_bearer_token: str | None = None
    rss_forum_feeds: tuple[str, ...] = (
        "https://www.reddit.com/r/netsec/.rss",
        "https://www.bleepingcomputer.com/feed/",
    )

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

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
            enable_github_collector=cls._env_bool("ENABLE_GITHUB_COLLECTOR", cls.enable_github_collector),
            enable_osint_feed_collector=cls._env_bool("ENABLE_OSINT_FEED_COLLECTOR", cls.enable_osint_feed_collector),
            enable_rss_forum_collector=cls._env_bool("ENABLE_RSS_FORUM_COLLECTOR", cls.enable_rss_forum_collector),
            enable_x_collector=cls._env_bool("ENABLE_X_COLLECTOR", cls.enable_x_collector),
            github_token=os.getenv("GITHUB_TOKEN") or None,
            x_bearer_token=os.getenv("X_BEARER_TOKEN") or None,
            rss_forum_feeds=tuple(
                feed.strip()
                for feed in os.getenv("RSS_FORUM_FEEDS", ",".join(cls.rss_forum_feeds)).split(",")
                if feed.strip()
            ),
        )
