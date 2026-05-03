"""Service bootstrap entrypoint."""

from __future__ import annotations

import atexit
import logging

import uvicorn

from src.alerts.router import AlertRouter
from src.api.app import app, record_collector_run, register_alert_router, register_scheduler, store
from src.config import Settings
from src.storage.raw_event_store import RawEvent
from src.workers.scheduler import CollectorScheduler

settings = Settings.from_env()
logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger(__name__)


def sample_collector() -> list[RawEvent]:
    """Placeholder collector for wiring checks."""
    return [RawEvent(source="sample", title="bootstrap-event", payload={"ok": True})]


def bootstrap() -> CollectorScheduler:
    alert_router = AlertRouter.from_config(
        [
            {"name": "critical-default", "channels": ["slack"], "severities": ["critical", "high"]},
        ]
    )
    register_alert_router(alert_router)

    scheduler = CollectorScheduler(
        collectors=[sample_collector],
        store=store,
        run_observer=lambda successes, failures, run_at: record_collector_run(successes, failures, run_at),
    )
    scheduler.start(interval_seconds=settings.scheduler_interval_seconds)
    register_scheduler(scheduler)
    atexit.register(scheduler.shutdown)
    return scheduler


if __name__ == "__main__":
    bootstrap()
    logger.info("starting HTTP API")
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
