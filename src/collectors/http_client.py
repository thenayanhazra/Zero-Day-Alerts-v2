from __future__ import annotations

import hashlib
import hmac
import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ErrorTelemetry:
    source_name: str
    method: str
    url: str
    status_code: int | None
    error_type: str
    message: str
    attempt: int
    timestamp: str


class RateLimiter:
    """Simple token interval limiter for a single source."""

    def __init__(self, requests_per_second: float) -> None:
        self._interval = 1.0 / max(requests_per_second, 0.001)
        self._next_allowed = 0.0
        self._lock = Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            if now < self._next_allowed:
                time.sleep(self._next_allowed - now)
            self._next_allowed = time.monotonic() + self._interval


class HttpClient:
    def __init__(self) -> None:
        self._rate_limiters: dict[str, RateLimiter] = {}

    def register_rate_limiter(self, source_name: str, requests_per_second: float) -> None:
        self._rate_limiters[source_name] = RateLimiter(requests_per_second=requests_per_second)

    def _sign_headers(
        self,
        headers: dict[str, str] | None,
        signing_secret: str | None,
        payload: dict[str, Any] | None,
    ) -> dict[str, str]:
        final_headers = dict(headers or {})
        if signing_secret:
            body = json.dumps(payload or {}, sort_keys=True, default=str).encode("utf-8")
            signature = hmac.new(signing_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
            final_headers["X-Signature-SHA256"] = signature
        return final_headers

    def request(
        self,
        *,
        source_name: str,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        timeout: int = 20,
        max_retries: int = 4,
        base_backoff_seconds: float = 0.75,
        signing_secret: str | None = None,
    ) -> requests.Response:
        limiter = self._rate_limiters.get(source_name)
        if limiter:
            limiter.wait()

        signed_headers = self._sign_headers(headers, signing_secret, json_body)
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=signed_headers,
                    params=params,
                    json=json_body,
                    timeout=timeout,
                )
                if response.status_code >= 500 or response.status_code == 429:
                    raise requests.HTTPError(
                        f"Retryable HTTP status: {response.status_code}", response=response
                    )
                response.raise_for_status()
                return response
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                telemetry = ErrorTelemetry(
                    source_name=source_name,
                    method=method,
                    url=url,
                    status_code=status_code,
                    error_type=type(exc).__name__,
                    message=str(exc),
                    attempt=attempt,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                LOGGER.warning("http_error_telemetry=%s", telemetry)
                if attempt >= max_retries:
                    break
                sleep_s = base_backoff_seconds * (2 ** (attempt - 1))
                sleep_s += random.uniform(0.0, 0.35)
                time.sleep(sleep_s)

        raise RuntimeError(f"HTTP request failed for {source_name}: {method} {url}") from last_error
