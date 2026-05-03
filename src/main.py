"""Service bootstrap entrypoint."""

from __future__ import annotations

import atexit
import logging
from collections.abc import Callable

import uvicorn

from src.api.app import app, store
from src.collectors import GitHubCollector, OSINTFeedCollector, RSSForumCollector, XCollector
from src.collectors.base import Collector as SourceCollector
from src.collectors.http_client import HttpClient
from src.config import Settings
from src.storage.raw_event_store import RawEvent
from src.workers.scheduler import CollectorScheduler

settings = Settings.from_env()
logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger(__name__)


def _collector_runner(collector: SourceCollector) -> Callable[[], list[RawEvent]]:
    def run() -> list[RawEvent]:
        raw_payloads = collector.fetch()
        events: list[RawEvent] = []
        for payload in raw_payloads:
            title = (
                str(payload.raw_content.get("title") or payload.raw_content.get("id") or payload.raw_id)
                if isinstance(payload.raw_content, dict)
                else str(payload.raw_id)
            )
            events.append(
                RawEvent(
                    source=payload.source_name,
                    title=title,
                    payload=payload.as_dict(),
                )
            )
        return events

    run.__name__ = f"{collector.source_name}_collector"
    return run


def build_collectors(settings: Settings) -> list[Callable[[], list[RawEvent]]]:
    http = HttpClient()
    enabled_names: list[str] = []
    collectors: list[Callable[[], list[RawEvent]]] = []

    if settings.enable_github_collector:
        collectors.append(_collector_runner(GitHubCollector(http=http, token=settings.github_token)))
        enabled_names.append("github")

    if settings.enable_osint_feed_collector:
        collectors.append(_collector_runner(OSINTFeedCollector(http=http)))
        enabled_names.append("osint_feeds")

    if settings.enable_rss_forum_collector:
        collectors.append(_collector_runner(RSSForumCollector(http=http, feeds=list(settings.rss_forum_feeds))))
        enabled_names.append("rss_forums")

    if settings.enable_x_collector:
        if settings.x_bearer_token:
            collectors.append(_collector_runner(XCollector(http=http, bearer_token=settings.x_bearer_token)))
            enabled_names.append("x_twitter")
        else:
            logger.warning("x collector enabled but X_BEARER_TOKEN is not set; skipping")

    logger.info("collector registry initialized", extra={"active_collectors": enabled_names})
    return collectors


def bootstrap() -> CollectorScheduler:
    collectors = build_collectors(settings)
    scheduler = CollectorScheduler(collectors=collectors, store=store)
    if collectors:
        scheduler.start(interval_seconds=settings.scheduler_interval_seconds)
    else:
        logger.warning("no collectors enabled; service readiness degraded", extra={"readiness_status": "degraded"})
    atexit.register(scheduler.shutdown)
    return scheduler


if __name__ == "__main__":
    bootstrap()
    logger.info("starting HTTP API")
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
