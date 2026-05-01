"""Security controls for secrets, outbound allowlists, and sanitization."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from html import escape
from typing import Protocol
from urllib.parse import urlparse


class SecretManager(Protocol):
    def get_secret(self, key: str) -> str | None: ...


@dataclass(slots=True)
class SecurityConfig:
    allowed_hosts: set[str]


def load_secret(key: str, secret_manager: SecretManager | None = None) -> str:
    env_value = os.getenv(key)
    if env_value:
        return env_value
    if secret_manager:
        managed_value = secret_manager.get_secret(key)
        if managed_value:
            return managed_value
    raise RuntimeError(f"missing secret: {key}")


def validate_outbound_url(url: str, config: SecurityConfig) -> None:
    host = (urlparse(url).hostname or "").lower()
    if host not in config.allowed_hosts:
        raise ValueError(f"host not allowlisted: {host}")


def sanitize_scraped_content(raw_content: str) -> str:
    stripped_scripts = re.sub(r"<script.*?>.*?</script>", "", raw_content, flags=re.IGNORECASE | re.DOTALL)
    return escape(stripped_scripts).strip()
