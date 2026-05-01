"""Logging, metrics, and dependency health checks."""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable

from prometheus_client import Counter, Histogram

collector_latency = Histogram("collector_latency", "Collector latency in seconds", ["collector"])
collector_errors = Counter("collector_errors", "Collector errors", ["collector"])
events_created = Counter("events_created", "Canonical events created", ["collector"])
alerts_sent = Counter("alerts_sent", "Alerts sent", ["channel"])


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = str(uuid.uuid4())
        return True


def configure_structured_logger(name: str = "zero_day_alerts") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '{"level":"%(levelname)s","message":"%(message)s","correlation_id":"%(correlation_id)s"}'
        )
        handler.setFormatter(formatter)
        handler.addFilter(CorrelationIdFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


@contextmanager
def track_collector_run(collector: str) -> None:
    start = time.perf_counter()
    try:
        yield
    except Exception:
        collector_errors.labels(collector=collector).inc()
        raise
    finally:
        collector_latency.labels(collector=collector).observe(time.perf_counter() - start)


@dataclass(slots=True)
class DependencyCheck:
    name: str
    checker: Callable[[], bool]


def run_dependency_health_checks(checks: list[DependencyCheck]) -> dict[str, str]:
    results: dict[str, str] = {}
    for check in checks:
        try:
            results[check.name] = "ok" if check.checker() else "degraded"
        except Exception:
            results[check.name] = "down"
    return results
