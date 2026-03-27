"""Security audit data models and classification policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Classification(Enum):
    """How a vulnerability finding should be treated."""

    FAIL = "fail"
    WARN = "warn"
    IGNORED = "ignored"


@dataclass
class AuditFinding:
    """A single vulnerability found by an audit tool."""

    package: str
    version: str
    vuln_id: str
    severity: str  # "critical" | "high" | "medium" | "low" | "unknown"
    description: str
    fix_versions: list[str]
    is_new_dep: bool = False

    def classify(self) -> Classification:
        """Apply the security policy: only FAIL on new + high/critical + fix available."""
        has_fix = len(self.fix_versions) > 0
        is_high = self.severity in ("high", "critical")
        if self.is_new_dep and is_high and has_fix:
            return Classification.FAIL
        return Classification.WARN


@dataclass
class SecurityReport:
    """Aggregated results from a security audit run."""

    findings: list[AuditFinding]
    ignored_ids: set[str] = field(default_factory=set)

    def _active_findings(self) -> list[tuple[AuditFinding, Classification]]:
        result = []
        for f in self.findings:
            if f.vuln_id in self.ignored_ids:
                continue
            result.append((f, f.classify()))
        return result

    @property
    def has_failures(self) -> bool:
        return any(c == Classification.FAIL for _, c in self._active_findings())

    @property
    def fail_count(self) -> int:
        return sum(1 for _, c in self._active_findings() if c == Classification.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for _, c in self._active_findings() if c == Classification.WARN)

    @property
    def ignored_count(self) -> int:
        return sum(1 for f in self.findings if f.vuln_id in self.ignored_ids)
