"""Security audit configuration from .agent-harness.yml."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


def _today() -> date:
    return date.today()


@dataclass
class SecurityConfig:
    """Parsed security configuration."""

    ignored_cves: set[str] = field(default_factory=set)
    base_branch: str = "origin/main"


def load_security_config(config: dict) -> SecurityConfig:
    """Extract security settings from the harness config dict."""
    security = config.get("security", {})
    if not isinstance(security, dict):
        return SecurityConfig()

    base_branch = security.get("base_branch", "origin/main")

    ignored_cves: set[str] = set()
    today = _today()

    for entry in security.get("ignore", []):
        if not isinstance(entry, dict):
            continue
        cve_id = entry.get("id", "")
        expires_str = entry.get("expires")

        if expires_str:
            try:
                expires = date.fromisoformat(expires_str)
                if expires < today:
                    continue  # Expired
            except ValueError:
                pass  # Bad date — include anyway

        ignored_cves.add(cve_id)

    return SecurityConfig(ignored_cves=ignored_cves, base_branch=base_branch)
