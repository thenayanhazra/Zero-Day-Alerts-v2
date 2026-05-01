from __future__ import annotations

from .base import Collector, RawPayload
from .http_client import HttpClient


class OSINTFeedCollector(Collector):
    source_name = "osint_feeds"
    source_type = "public_api"

    def __init__(self, http: HttpClient) -> None:
        self.http = http
        self.http.register_rate_limiter(self.source_name, requests_per_second=1.0)

    def fetch(self) -> list[RawPayload]:
        payloads: list[RawPayload] = []

        kev = self.http.request(
            source_name=self.source_name,
            method="GET",
            url="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        ).json()
        for item in kev.get("vulnerabilities", []):
            rid = item.get("cveID") or item.get("vulnerabilityName")
            payloads.append(self.normalize_raw_item(raw_id=str(rid), raw_content=item, raw_url="https://www.cisa.gov/known-exploited-vulnerabilities-catalog"))

        nvd = self.http.request(
            source_name=self.source_name,
            method="GET",
            url="https://services.nvd.nist.gov/rest/json/cves/2.0",
            params={"resultsPerPage": 200},
        ).json()
        for vuln in nvd.get("vulnerabilities", []):
            cve = vuln.get("cve", {})
            rid = cve.get("id")
            payloads.append(self.normalize_raw_item(raw_id=str(rid), raw_content=vuln, raw_url=f"https://nvd.nist.gov/vuln/detail/{rid}" if rid else None))

        exploitdb = self.http.request(
            source_name=self.source_name,
            method="GET",
            url="https://gitlab.com/exploit-database/exploitdb/-/raw/main/files_exploits.csv",
        ).text
        for line in exploitdb.splitlines()[1:201]:
            cols = line.split(",")
            if not cols:
                continue
            raw_id = cols[0]
            payloads.append(self.normalize_raw_item(raw_id=f"edb:{raw_id}", raw_content={"csv_line": line}, raw_url="https://www.exploit-db.com/"))

        return payloads
