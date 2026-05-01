"""Service bootstrap entrypoint."""

from __future__ import annotations

import atexit
import logging

import uvicorn

from src.api.app import app
from src.storage.raw_event_store import InMemoryRawEventStore, RawEvent
from src.workers.scheduler import CollectorScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sample_collector() -> list[RawEvent]:
    """Placeholder collector for wiring checks."""
    return [RawEvent(source="sample", title="bootstrap-event", payload={"ok": True})]


def bootstrap() -> CollectorScheduler:
    store = InMemoryRawEventStore()
    scheduler = CollectorScheduler(collectors=[sample_collector], store=store)
    scheduler.start(interval_seconds=120)
    atexit.register(scheduler.shutdown)
    return scheduler


if __name__ == "__main__":
    bootstrap()
    logger.info("starting HTTP API")
    uvicorn.run(app, host="0.0.0.0", port=8000)
