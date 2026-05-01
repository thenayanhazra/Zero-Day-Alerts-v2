from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from hashlib import sha256

_CVE_PATTERN = re.compile(r"\bCVE-(\d{4})-(\d{4,7})\b", flags=re.IGNORECASE)
_URL_PATTERN = re.compile(r"\bhttps?://[^\s<>'\"]+", flags=re.IGNORECASE)
_SHA256_PATTERN = re.compile(r"\b[a-fA-F0-9]{64}\b")
_SHA1_PATTERN = re.compile(r"\b[a-fA-F0-9]{40}\b")
_MD5_PATTERN = re.compile(r"\b[a-fA-F0-9]{32}\b")
_IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_DOMAIN_PATTERN = re.compile(
    r"\b(?=.{1,253}\b)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:[a-zA-Z]{2,63})\b"
)

_POC_PATTERNS = [
    re.compile(r"\bproof[-\s]?of[-\s]?concept\b", flags=re.IGNORECASE),
    re.compile(r"\bpoc\b", flags=re.IGNORECASE),
    re.compile(r"\bexploit\s+code\b", flags=re.IGNORECASE),
    re.compile(r"\bgithub\.com/.+/(exploit|poc)", flags=re.IGNORECASE),
]

_EXPLOITATION_PATTERNS = [
    re.compile(r"\bexploited\s+in\s+the\s+wild\b", flags=re.IGNORECASE),
    re.compile(r"\bactive\s+exploitation\b", flags=re.IGNORECASE),
    re.compile(r"\bund(er|)\s+active\s+attack\b", flags=re.IGNORECASE),
    re.compile(r"\bzero[-\s]?day\b", flags=re.IGNORECASE),
]


@dataclass(slots=True)
class ParsedIndicators:
    cve_ids: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    hashes: list[str] = field(default_factory=list)
    ips: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    poc_available: bool = False
    exploitation_in_wild: bool = False


def _dedupe_sorted(values: set[str]) -> list[str]:
    return sorted(values, key=lambda x: x.lower())


def _is_valid_cve(year_text: str, seq_text: str) -> bool:
    year = int(year_text)
    if year < 1999 or year > 2100:
        return False
    return int(seq_text) > 0


def _extract_cves(text: str) -> list[str]:
    out: set[str] = set()
    for match in _CVE_PATTERN.finditer(text):
        year_text, seq_text = match.groups()
        if _is_valid_cve(year_text, seq_text):
            out.add(f"CVE-{year_text}-{int(seq_text)}")
    return _dedupe_sorted(out)


def _extract_ips(text: str) -> list[str]:
    out: set[str] = set()
    for match in _IPV4_PATTERN.finditer(text):
        candidate = match.group(0)
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            continue
        out.add(candidate)
    return _dedupe_sorted(out)


def parse_indicators(text: str) -> ParsedIndicators:
    urls = _dedupe_sorted(set(_URL_PATTERN.findall(text)))

    hashes = _dedupe_sorted(
        set(_SHA256_PATTERN.findall(text))
        | set(_SHA1_PATTERN.findall(text))
        | set(_MD5_PATTERN.findall(text))
    )
    ips = _extract_ips(text)

    domain_candidates = set(_DOMAIN_PATTERN.findall(text))
    domains = _dedupe_sorted({d for d in domain_candidates if d not in {"localhost"}})

    poc_available = any(p.search(text) for p in _POC_PATTERNS)
    exploitation_in_wild = any(p.search(text) for p in _EXPLOITATION_PATTERNS)

    return ParsedIndicators(
        cve_ids=_extract_cves(text),
        urls=urls,
        hashes=hashes,
        ips=ips,
        domains=domains,
        poc_available=poc_available,
        exploitation_in_wild=exploitation_in_wild,
    )


def stable_text_digest(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return sha256(normalized.encode("utf-8")).hexdigest()
