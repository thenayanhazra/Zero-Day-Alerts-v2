# Zero Day Alerts v2

## Operational baseline

### Storage
- Database models and migration were added for:
  - raw items
  - canonical events
  - scores
  - alerts
  - source health

### Redis queues
- `ingestion_jobs` queue for normal ingestion.
- `ingestion_retry_jobs` queue for retried jobs.

### Observability
- Structured JSON logs with `correlation_id` field.
- Prometheus metrics:
  - `collector_latency`
  - `collector_errors`
  - `events_created`
  - `alerts_sent`
- Dependency health checks per collector dependency.

### Security controls
- Secrets loaded from environment first, then optional secret manager.
- Outbound HTTP collectors constrained by allowlisted hostnames.
- Sanitization for scraped content strips script tags and escapes HTML.

## API key rotation runbook
1. Create a new key in your secret manager/provider.
2. Store the new value under a versioned key (for example `API_KEY_V2`).
3. Deploy service with dual-read logic (`API_KEY_V2` first, `API_KEY` fallback).
4. Verify successful requests and alert delivery in metrics.
5. Revoke old key at provider.
6. Remove fallback from code/config in next deploy.
7. Document rotation date, owner, and impacted collectors.
