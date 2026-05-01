from __future__ import annotations

from typing import Any

from .base import Collector, RawPayload
from .http_client import HttpClient


class GitHubCollector(Collector):
    source_name = "github"
    source_type = "api"

    def __init__(self, http: HttpClient, token: str | None = None) -> None:
        self.http = http
        self.token = token
        self.http.register_rate_limiter(self.source_name, requests_per_second=1.5)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _fetch_endpoint(self, url: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        response = self.http.request(
            source_name=self.source_name,
            method="GET",
            url=url,
            headers=self._headers(),
            params=params,
        )
        body = response.json()
        if isinstance(body, list):
            return body
        if isinstance(body, dict) and "items" in body:
            return body["items"]
        return [body]

    def fetch(self) -> list[RawPayload]:
        payloads: list[RawPayload] = []

        advisory_url = "https://api.github.com/advisories"
        for record in self._fetch_endpoint(advisory_url, {"per_page": 100}):
            rid = record.get("ghsa_id") or record.get("cve_id") or str(record.get("id"))
            payloads.append(self.normalize_raw_item(raw_id=rid, raw_content=record, raw_url=record.get("html_url")))

        repo_search = "https://api.github.com/search/repositories"
        repo_params = {"q": "security exploit cve in:description,readme", "sort": "updated", "per_page": 25}
        for record in self._fetch_endpoint(repo_search, repo_params):
            rid = str(record.get("id"))
            payloads.append(self.normalize_raw_item(raw_id=f"repo:{rid}", raw_content=record, raw_url=record.get("html_url")))

        events_url = "https://api.github.com/events"
        for record in self._fetch_endpoint(events_url):
            if "release" in str(record.get("type", "")).lower() or "security" in str(record).lower():
                rid = str(record.get("id"))
                payloads.append(self.normalize_raw_item(raw_id=f"event:{rid}", raw_content=record, raw_url=record.get("repo", {}).get("url")))

        return payloads
