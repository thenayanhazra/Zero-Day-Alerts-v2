"""HTTP API application for service status endpoints."""

from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(title="Zero-Day Alerts API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Basic liveness check."""
    return {"status": "ok"}


@app.get("/readiness")
def readiness() -> dict[str, str]:
    """Basic readiness check with timestamp."""
    return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}
