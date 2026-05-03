"""HTTP API application for service status endpoints and event dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from src.alerts.router import AlertRouter
from src.storage.raw_event_store import InMemoryRawEventStore, RawEvent
from src.workers.scheduler import CollectorScheduler
from src.config import Settings
from src.storage import build_raw_event_store
from src.storage.raw_event_store import RawEvent

app = FastAPI(title="Zero-Day Alerts API", version="0.1.0")
store = build_raw_event_store(Settings.from_env())


@dataclass(slots=True)
class CollectorRunStatus:
    """Status for the most recent collector cycle."""

    timestamp: datetime
    successes: int
    failures: int


@dataclass(slots=True)
class ReadinessState:
    """Mutable state used by readiness diagnostics."""

    scheduler: CollectorScheduler | None = None
    alert_router: AlertRouter | None = None
    collector_runs: list[CollectorRunStatus] = field(default_factory=list)
    collector_window: timedelta = field(default=timedelta(minutes=15))


readiness_state = ReadinessState()


def register_scheduler(scheduler: CollectorScheduler) -> None:
    """Register scheduler dependency for readiness checks."""
    readiness_state.scheduler = scheduler


def register_alert_router(router: AlertRouter) -> None:
    """Register alert router dependency for readiness checks."""
    readiness_state.alert_router = router


def record_collector_run(successes: int, failures: int, at: datetime | None = None) -> None:
    """Record collector execution outcome for readiness checks."""
    run = CollectorRunStatus(timestamp=at or datetime.now(timezone.utc), successes=successes, failures=failures)
    readiness_state.collector_runs.append(run)
    cutoff = run.timestamp - readiness_state.collector_window
    readiness_state.collector_runs = [item for item in readiness_state.collector_runs if item.timestamp >= cutoff]


def _seed_events() -> None:
    """Seed dashboard with illustrative events for local development."""
    store.write_many(
        [
            RawEvent(
                source="cisa-kev",
                title="CVE-2026-10001 exploited in the wild",
                payload={"severity": "critical", "vendor": "ExampleSoft"},
            ),
            RawEvent(
                source="github-advisories",
                title="CVE-2026-10077 remote code execution advisory",
                payload={"severity": "high", "vendor": "Fabrikam"},
            ),
        ]
    )


_seed_events()


@app.get("/health")
def health() -> dict[str, str]:
    """Basic liveness check."""
    return {"status": "ok"}


def _is_scheduler_running() -> bool:
    return bool(readiness_state.scheduler and readiness_state.scheduler.scheduler.running)


def _is_store_connected() -> bool:
    try:
        store.count()
        return True
    except Exception:
        return False


def _collector_window_summary(now: datetime) -> dict[str, Any]:
    cutoff = now - readiness_state.collector_window
    recent_runs = [run for run in readiness_state.collector_runs if run.timestamp >= cutoff]
    total_successes = sum(run.successes for run in recent_runs)
    total_failures = sum(run.failures for run in recent_runs)
    return {
        "window_seconds": int(readiness_state.collector_window.total_seconds()),
        "runs": len(recent_runs),
        "successes": total_successes,
        "failures": total_failures,
        "latest": recent_runs[-1].timestamp.isoformat() if recent_runs else None,
        "healthy": bool(recent_runs) and total_successes > 0 and total_failures == 0,
    }


def _is_router_operational() -> bool:
    router = readiness_state.alert_router
    return router is not None and router.route_count > 0


@app.get("/readiness")
def readiness() -> dict[str, Any]:
    """Readiness check with component diagnostics."""
    now = datetime.now(timezone.utc)
    collector = _collector_window_summary(now)

    diagnostics = {
        "scheduler": {"running": _is_scheduler_running()},
        "store": {"connected": _is_store_connected()},
        "collector": collector,
        "alert_router": {"operational": _is_router_operational()},
    }
    critical_healthy = (
        diagnostics["scheduler"]["running"]
        and diagnostics["store"]["connected"]
        and diagnostics["collector"]["healthy"]
        and diagnostics["alert_router"]["operational"]
    )

    return {
        "status": "ready" if critical_healthy else "not_ready",
        "degraded": not critical_healthy,
        "timestamp": now.isoformat(),
        "diagnostics": diagnostics,
    }


@app.get("/events")
def events() -> list[dict[str, object]]:
    """Return captured raw events as JSON."""
    return [{"source": event.source, "title": event.title, "payload": event.payload} for event in store.all()]


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    """Simple web dashboard showing captured zero-day events."""
    refresh_interval_seconds = 10
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(event.source)}</td>"
        f"<td>{escape(event.title)}</td>"
        f"<td>{escape(str(event.payload.get('severity', 'unknown')))}</td>"
        f"<td>{escape(str(event.payload.get('vendor', 'unknown')))}</td>"
        "</tr>"
        for event in reversed(store.all())
    )

    return f"""
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
      <meta charset=\"UTF-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
      <title>Zero-Day Alerts Dashboard</title>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 2rem; background: #0f172a; color: #e2e8f0; }}
        h1 {{ margin-bottom: 0.25rem; }}
        .subtitle {{ color: #94a3b8; margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; background: #111827; }}
        th, td {{ border: 1px solid #1f2937; padding: 0.75rem; text-align: left; }}
        th {{ background: #1e293b; }}
        tr:nth-child(even) {{ background: #0b1220; }}
      </style>
    </head>
    <body>
      <h1>Zero-Day Alerts</h1>
      <p class=\"subtitle\">Captured events currently held in memory: {store.count()}</p>
      <p class=\"subtitle\">Refresh interval: <span id=\"refresh-interval\">{refresh_interval_seconds}</span> seconds · Last updated: <span id=\"last-updated\">Never</span></p>
      <table>
        <thead>
          <tr><th>Source</th><th>Title</th><th>Severity</th><th>Vendor</th></tr>
        </thead>
        <tbody id=\"events-body\">
          {rows if rows else '<tr><td colspan="4">No events captured yet.</td></tr>'}
        </tbody>
      </table>
      <script>
        const refreshIntervalSeconds = {refresh_interval_seconds};
        const eventsBody = document.getElementById('events-body');
        const lastUpdated = document.getElementById('last-updated');

        function cellWithText(value) {{
          const td = document.createElement('td');
          td.textContent = String(value);
          return td;
        }}

        function renderRows(events) {{
          eventsBody.replaceChildren();

          if (!events.length) {{
            const emptyRow = document.createElement('tr');
            const emptyCell = document.createElement('td');
            emptyCell.colSpan = 4;
            emptyCell.textContent = 'No events captured yet.';
            emptyRow.appendChild(emptyCell);
            eventsBody.appendChild(emptyRow);
            return;
          }}

          [...events].reverse().forEach((event) => {{
            const row = document.createElement('tr');
            row.appendChild(cellWithText(event.source ?? ''));
            row.appendChild(cellWithText(event.title ?? ''));
            row.appendChild(cellWithText(event.payload?.severity ?? 'unknown'));
            row.appendChild(cellWithText(event.payload?.vendor ?? 'unknown'));
            eventsBody.appendChild(row);
          }});
        }}

        async function refreshEvents() {{
          try {{
            const response = await fetch('/events', {{ headers: {{ Accept: 'application/json' }} }});
            if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
            const events = await response.json();
            renderRows(Array.isArray(events) ? events : []);
            lastUpdated.textContent = new Date().toLocaleTimeString();
          }} catch (_err) {{
            lastUpdated.textContent = 'Update failed';
          }}
        }}

        refreshEvents();
        setInterval(refreshEvents, refreshIntervalSeconds * 1000);
      </script>
    </body>
    </html>
    """
