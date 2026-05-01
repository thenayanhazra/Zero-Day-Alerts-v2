# Zero-Day-Alerts-v2

Python service skeleton for collecting, normalizing, scoring, enriching, and alerting on zero-day intelligence.

## Architecture Summary

- `src/collectors/`: Pulls raw vulnerability/security events from external feeds and APIs.
- `src/normalization/`: Converts collector-specific payloads into internal canonical event models.
- `src/scoring/`: Assigns risk/priority scores to normalized events.
- `src/enrichment/`: Adds contextual metadata (vendor, exploit status, affected products, etc.).
- `src/storage/`: Persists raw and processed events.
- `src/alerts/`: Emits notifications to sinks (Slack, Discord, PagerDuty, etc.).
- `src/api/`: FastAPI service layer with operational endpoints.
- `src/workers/`: Background jobs and schedulers.
- `configs/`: Environment-specific configuration files.
- `infra/`: Deployment, IaC, and runtime manifests.
- `tests/`: Test suite.

Current bootstrap includes:
- FastAPI app with `/health` and `/readiness` endpoints.
- APScheduler-based worker (`CollectorScheduler`) that runs collectors on intervals.
- In-memory raw event storage adapter for local wiring.

## Local Run

### 1) Create virtual environment and install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2) Configure environment

```bash
cp .env.example .env
# edit values as needed
```

### 3) Start service

```bash
python -m src.main
```

The API will be available at `http://localhost:8000`.

### 4) Check health endpoints

```bash
curl http://localhost:8000/health
curl http://localhost:8000/readiness
```
