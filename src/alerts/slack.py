from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from .router import AlertEvent


@dataclass
class SlackSender:
    webhook_url: str
    timeout_seconds: float = 5.0

    def send(self, event: AlertEvent) -> dict[str, Any]:
        payload = {
            "text": f"[{event.severity.upper()}] {event.title or event.event_id}",
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*Source:* {event.source}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": event.body or "(no details)"}},
            ],
        }
        response = requests.post(self.webhook_url, json=payload, timeout=self.timeout_seconds)
        response.raise_for_status()
        return {"ok": True, "status_code": response.status_code, "channel": "slack"}
