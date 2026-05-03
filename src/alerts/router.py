from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

from src.config import Settings

from .policies import AlertPolicyEngine, AlertState

LOGGER = logging.getLogger(__name__)


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


class AlertSink(Protocol):
    def send(self, event: AlertEvent) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SinkDispatchResult:
    sink: str
    ok: bool
    attempts: int
    timed_out: bool = False
    error: str | None = None
    response: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DispatchResult:
    event_id: str
    allowed: bool
    reason: str
    skipped_duplicate: bool
    channels: tuple[str, ...]
    sink_results: tuple[SinkDispatchResult, ...]


class AlertDispatcher:
    """Apply policy and dispatch alert events with retry/timeout + idempotency controls."""

    def __init__(
        self,
        *,
        router: AlertRouter,
        policy_engine: AlertPolicyEngine,
        sinks: Mapping[str, AlertSink],
        settings: Settings,
        state_resolver: Callable[[AlertEvent], AlertState | None] | None = None,
        on_sent: Callable[[AlertEvent], None] | None = None,
    ):
        self._router = router
        self._policy_engine = policy_engine
        self._sinks = dict(sinks)
        self._settings = settings
        self._state_resolver = state_resolver or (lambda _event: None)
        self._on_sent = on_sent
        self._seen_event_keys: set[str] = set()

    def dispatch(self, event: AlertEvent) -> DispatchResult:
        event_key = self._event_key(event)
        if event_key in self._seen_event_keys:
            LOGGER.info("alert_dispatch_duplicate", extra={"event_id": event.event_id, "event_key": event_key})
            return DispatchResult(event.event_id, False, "suppressed: duplicate event key", True, (), ())

        state = self._state_resolver(event)
        decision = self._policy_engine.evaluate(event, state)
        if not decision.allowed:
            LOGGER.info(
                "alert_dispatch_suppressed",
                extra={"event_id": event.event_id, "event_key": event_key, "reason": decision.reason},
            )
            return DispatchResult(event.event_id, False, decision.reason, False, (), ())

        channels = self._enabled_channels(self._router.route_event(event), event.severity)
        results = tuple(self._dispatch_channel(channel, event) for channel in channels)

        if any(result.ok for result in results):
            self._seen_event_keys.add(event_key)
            if self._on_sent:
                self._on_sent(event)

        return DispatchResult(event.event_id, True, decision.reason, False, channels, results)

    def _enabled_channels(self, channels: tuple[str, ...], severity: str) -> tuple[str, ...]:
        enabled = {
            "email": self._settings.alert_sink_email_enabled,
            "slack": self._settings.alert_sink_slack_enabled,
            "webhook": self._settings.alert_sink_webhook_enabled,
        }
        severity_level = self._severity_rank(severity)
        thresholds = {
            "email": self._severity_rank(self._settings.alert_sink_email_min_severity),
            "slack": self._severity_rank(self._settings.alert_sink_slack_min_severity),
            "webhook": self._severity_rank(self._settings.alert_sink_webhook_min_severity),
        }
        return tuple(
            channel
            for channel in channels
            if enabled.get(channel, False) and severity_level >= thresholds.get(channel, severity_level)
        )

    def _dispatch_channel(self, channel: str, event: AlertEvent) -> SinkDispatchResult:
        sink = self._sinks.get(channel)
        if sink is None:
            LOGGER.error("alert_dispatch_missing_sink", extra={"event_id": event.event_id, "sink": channel})
            return SinkDispatchResult(channel, False, attempts=0, error="missing sink")

        for attempt in range(1, self._settings.alert_sink_retry_count + 2):
            try:
                response = self._send_with_timeout(sink, event, self._settings.alert_sink_timeout_seconds)
                LOGGER.info(
                    "alert_dispatch_success",
                    extra={"event_id": event.event_id, "sink": channel, "attempt": attempt},
                )
                return SinkDispatchResult(channel, True, attempts=attempt, response=response)
            except TimeoutError as exc:
                LOGGER.warning(
                    "alert_dispatch_timeout",
                    extra={"event_id": event.event_id, "sink": channel, "attempt": attempt},
                )
                last_error = str(exc)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception(
                    "alert_dispatch_failure",
                    extra={"event_id": event.event_id, "sink": channel, "attempt": attempt},
                )
                last_error = str(exc)
        return SinkDispatchResult(channel, False, attempts=self._settings.alert_sink_retry_count + 1, error=last_error)

    @staticmethod
    def _send_with_timeout(sink: AlertSink, event: AlertEvent, timeout_seconds: float) -> dict[str, Any]:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(sink.send, event)
            try:
                return future.result(timeout=timeout_seconds)
            except FutureTimeoutError as exc:
                raise TimeoutError(f"send timed out after {timeout_seconds}s") from exc

    @staticmethod
    def _severity_rank(severity: str) -> int:
        levels = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        return levels.get(severity.lower(), 0)

    @staticmethod
    def _event_key(event: AlertEvent) -> str:
        return f"{event.source}:{event.event_id}:{event.severity}"
