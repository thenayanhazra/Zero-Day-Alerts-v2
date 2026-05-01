from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from .router import AlertEvent


@dataclass
class WebhookSender:
    endpoint: str
    timeout_seconds: float = 5.0

    def send(self, event: AlertEvent) -> dict[str, Any]:
        payload = {
            "event_id": event.event_id,
            "source": event.source,
            "severity": event.severity,
            "tags": sorted(event.tags),
            "title": event.title,
            "body": event.body,
            "metadata": dict(event.metadata),
        }
        response = requests.post(self.endpoint, json=payload, timeout=self.timeout_seconds)
        response.raise_for_status()
        return {"ok": True, "status_code": response.status_code, "channel": "webhook"}
