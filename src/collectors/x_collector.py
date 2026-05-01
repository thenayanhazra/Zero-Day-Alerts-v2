from __future__ import annotations

from .base import Collector, RawPayload
from .http_client import HttpClient


class XCollector(Collector):
    source_name = "x_twitter"
    source_type = "social_api"

    def __init__(self, http: HttpClient, bearer_token: str) -> None:
        self.http = http
        self.bearer_token = bearer_token
        self.http.register_rate_limiter(self.source_name, requests_per_second=0.5)

    def fetch(self) -> list[RawPayload]:
        query = '(cve OR exploit OR "proof of concept" OR ransomware) lang:en -is:retweet'
        url = "https://api.x.com/2/tweets/search/recent"
        resp = self.http.request(
            source_name=self.source_name,
            method="GET",
            url=url,
            headers={"Authorization": f"Bearer {self.bearer_token}"},
            params={
                "query": query,
                "max_results": 100,
                "tweet.fields": "created_at,author_id,lang,public_metrics,entities",
                "expansions": "author_id",
            },
        )
        data = resp.json().get("data", [])
        payloads: list[RawPayload] = []
        for tweet in data:
            rid = str(tweet.get("id"))
            raw_url = f"https://x.com/i/web/status/{rid}" if rid else None
            payloads.append(self.normalize_raw_item(raw_id=rid, raw_content=tweet, raw_url=raw_url))
        return payloads
