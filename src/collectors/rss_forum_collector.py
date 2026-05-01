from __future__ import annotations

import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from .base import Collector, RawPayload
from .http_client import HttpClient


class RSSForumCollector(Collector):
    source_name = "rss_forums"
    source_type = "rss_html"

    def __init__(self, http: HttpClient, feeds: list[str]) -> None:
        self.http = http
        self.feeds = feeds
        self.http.register_rate_limiter(self.source_name, requests_per_second=1.0)

    def _extract_html(self, url: str) -> dict[str, str]:
        resp = self.http.request(source_name=self.source_name, method="GET", url=url)
        soup = BeautifulSoup(resp.text, "html.parser")
        title = (soup.title.string or "").strip() if soup.title else ""
        body = "\n".join(p.get_text(" ", strip=True) for p in soup.find_all("p")[:20])
        return {"title": title, "excerpt": body}

    def fetch(self) -> list[RawPayload]:
        payloads: list[RawPayload] = []
        for feed_url in self.feeds:
            feed_xml = self.http.request(source_name=self.source_name, method="GET", url=feed_url).text
            root = ET.fromstring(feed_xml)
            items = root.findall(".//item") + root.findall(".//{http://www.w3.org/2005/Atom}entry")

            for item in items:
                entry_link = item.findtext("link")
                if entry_link is None:
                    atom_link = item.find("{http://www.w3.org/2005/Atom}link")
                    entry_link = atom_link.attrib.get("href") if atom_link is not None else None

                title = item.findtext("title") or ""
                guid = item.findtext("guid") or item.findtext("id") or entry_link or title
                content = {"title": title, "link": entry_link, "feed": feed_url}
                if entry_link:
                    content["html"] = self._extract_html(entry_link)

                payloads.append(
                    self.normalize_raw_item(
                        raw_id=str(guid),
                        raw_content=content,
                        raw_url=entry_link,
                    )
                )
        return payloads
