from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from enum import Enum

from .router import AlertEvent


class AlertStatus(str, Enum):
    NEW = "new"
    SENT = "sent"
    ACKED = "acked"
    CLOSED = "closed"


@dataclass
class AlertState:
    alert_id: str
    event_id: str
    status: AlertStatus
    acked_by: str | None = None
    acked_at: datetime | None = None
    source: str = ""
    last_sent_at: datetime | None = None
    send_count_window: int = 0
    window_started_at: datetime | None = None


@dataclass(frozen=True)
class MaintenanceWindow:
    name: str
    start: time
    end: time

    def contains(self, dt: datetime) -> bool:
        t = dt.timetz().replace(tzinfo=None)
        if self.start <= self.end:
            return self.start <= t <= self.end
        return t >= self.start or t <= self.end


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str = "allowed"


class AlertPolicyEngine:
    def __init__(
        self,
        dedupe_window: timedelta,
        max_frequency: int,
        frequency_window: timedelta,
        maintenance_windows: tuple[MaintenanceWindow, ...] = (),
    ):
        self.dedupe_window = dedupe_window
        self.max_frequency = max_frequency
        self.frequency_window = frequency_window
        self.maintenance_windows = maintenance_windows

    def evaluate(self, event: AlertEvent, state: AlertState | None, now: datetime | None = None) -> PolicyDecision:
        now = now or datetime.now(timezone.utc)

        if any(window.contains(now) for window in self.maintenance_windows):
            return PolicyDecision(False, "suppressed: maintenance window")

        if state is None:
            return PolicyDecision(True)

        if state.last_sent_at and now - state.last_sent_at < self.dedupe_window:
            return PolicyDecision(False, "suppressed: dedupe window")

        if state.window_started_at is None or now - state.window_started_at >= self.frequency_window:
            return PolicyDecision(True)

        if state.send_count_window >= self.max_frequency:
            return PolicyDecision(False, "suppressed: max frequency reached")

        return PolicyDecision(True)

    def mark_sent(self, state: AlertState, now: datetime | None = None) -> AlertState:
        now = now or datetime.now(timezone.utc)
        if state.window_started_at is None or now - state.window_started_at >= self.frequency_window:
            state.window_started_at = now
            state.send_count_window = 0

        state.last_sent_at = now
        state.send_count_window += 1
        state.status = AlertStatus.SENT
        return state

    def acknowledge(self, state: AlertState, actor: str, now: datetime | None = None) -> AlertState:
        state.status = AlertStatus.ACKED
        state.acked_by = actor
        state.acked_at = now or datetime.now(timezone.utc)
        return state
