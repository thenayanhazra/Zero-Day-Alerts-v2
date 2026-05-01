"""Redis-backed ingestion and retry queues."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import redis

INGESTION_QUEUE = "ingestion_jobs"
RETRY_QUEUE = "ingestion_retry_jobs"


@dataclass(slots=True)
class QueueConfig:
    redis_url: str
    ingestion_queue: str = INGESTION_QUEUE
    retry_queue: str = RETRY_QUEUE


class RedisQueue:
    def __init__(self, config: QueueConfig) -> None:
        self.config = config
        self.client = redis.Redis.from_url(config.redis_url, decode_responses=True)

    def enqueue_ingestion(self, job: dict[str, Any]) -> int:
        return int(self.client.rpush(self.config.ingestion_queue, json.dumps(job)))

    def enqueue_retry(self, job: dict[str, Any]) -> int:
        return int(self.client.rpush(self.config.retry_queue, json.dumps(job)))

    def dequeue_ingestion(self, timeout_seconds: int = 5) -> dict[str, Any] | None:
        result = self.client.blpop(self.config.ingestion_queue, timeout=timeout_seconds)
        if not result:
            return None
        _, payload = result
        return json.loads(payload)

    def dequeue_retry(self, timeout_seconds: int = 5) -> dict[str, Any] | None:
        result = self.client.blpop(self.config.retry_queue, timeout=timeout_seconds)
        if not result:
            return None
        _, payload = result
        return json.loads(payload)
