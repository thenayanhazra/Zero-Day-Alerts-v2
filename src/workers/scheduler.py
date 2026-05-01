"""Interval scheduler that runs collectors and persists raw events."""

from __future__ import annotations

import logging
from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler

from src.storage.raw_event_store import RawEvent, RawEventStore

logger = logging.getLogger(__name__)
Collector = Callable[[], list[RawEvent]]


class CollectorScheduler:
    def __init__(self, collectors: list[Collector], store: RawEventStore) -> None:
        self.collectors = collectors
        self.store = store
        self.scheduler = BackgroundScheduler()

    def _run_collectors(self) -> None:
        total = 0
        failures = 0
        for collector in self.collectors:
            try:
                events = collector()
                total += self.store.write_many(events)
            except Exception:
                failures += 1
                logger.exception("collector execution failed", extra={"collector": getattr(collector, "__name__", "unknown")})
        logger.info("collector run complete", extra={"raw_events_written": total, "collector_failures": failures})

    def start(self, interval_seconds: int = 60) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")
        if self.scheduler.running:
            logger.info("collector scheduler already running")
            return

        self.scheduler.add_job(
            self._run_collectors,
            trigger="interval",
            seconds=interval_seconds,
            id="collector-interval-job",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.start()
        logger.info("collector scheduler started", extra={"interval_seconds": interval_seconds})

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("collector scheduler stopped")
