"""HTTP API application for service status endpoints and event dashboard."""

from datetime import datetime, timezone
from html import escape

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from src.config import Settings
from src.storage import build_raw_event_store
from src.storage.raw_event_store import RawEvent

app = FastAPI(title="Zero-Day Alerts API", version="0.1.0")
store = build_raw_event_store(Settings.from_env())


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


@app.get("/readiness")
def readiness() -> dict[str, str]:
    """Basic readiness check with timestamp."""
    return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/events")
def events() -> list[dict[str, object]]:
    """Return captured raw events as JSON."""
    return [{"source": event.source, "title": event.title, "payload": event.payload} for event in store.all()]


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    """Simple web dashboard showing captured zero-day events."""
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
      <table>
        <thead>
          <tr><th>Source</th><th>Title</th><th>Severity</th><th>Vendor</th></tr>
        </thead>
        <tbody>
          {rows if rows else '<tr><td colspan="4">No events captured yet.</td></tr>'}
        </tbody>
      </table>
    </body>
    </html>
    """
