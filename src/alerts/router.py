from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class AlertEvent:
    """Normalized event payload used for routing and delivery."""

    event_id: str
    source: str
    severity: str
    tags: frozenset[str] = field(default_factory=frozenset)
    title: str = ""
    body: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "AlertEvent":
        tags = payload.get("tags", ())
        return cls(
            event_id=str(payload["event_id"]),
            source=str(payload.get("source", "unknown")),
            severity=str(payload.get("severity", "info")).lower(),
            tags=frozenset(str(tag) for tag in tags),
            title=str(payload.get("title", "")),
            body=str(payload.get("body", "")),
            metadata=dict(payload),
        )


@dataclass(frozen=True)
class AlertRoute:
    name: str
    channels: tuple[str, ...]
    severities: frozenset[str] = field(default_factory=frozenset)
    required_tags: frozenset[str] = field(default_factory=frozenset)
    blocked_tags: frozenset[str] = field(default_factory=frozenset)

    def matches(self, event: AlertEvent) -> bool:
        if self.severities and event.severity not in self.severities:
            return False
        if self.required_tags and not self.required_tags.issubset(event.tags):
            return False
        if self.blocked_tags and self.blocked_tags.intersection(event.tags):
            return False
        return True


class AlertRouter:
    """Routes events to one or more delivery channels based on severity + tags."""

    def __init__(self, routes: Iterable[AlertRoute]):
        self._routes: tuple[AlertRoute, ...] = tuple(routes)

    @classmethod
    def from_config(cls, config: Sequence[Mapping[str, object]]) -> "AlertRouter":
        routes: list[AlertRoute] = []
        for item in config:
            routes.append(
                AlertRoute(
                    name=str(item["name"]),
                    channels=tuple(str(c) for c in item.get("channels", [])),
                    severities=frozenset(str(s).lower() for s in item.get("severities", [])),
                    required_tags=frozenset(str(t) for t in item.get("required_tags", [])),
                    blocked_tags=frozenset(str(t) for t in item.get("blocked_tags", [])),
                )
            )
        return cls(routes)

    @property
    def route_count(self) -> int:
        return len(self._routes)

    def route_event(self, event: AlertEvent) -> tuple[str, ...]:
        channels: list[str] = []
        for route in self._routes:
            if route.matches(event):
                channels.extend(route.channels)
        return tuple(dict.fromkeys(channels))
