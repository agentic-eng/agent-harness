"""Gitleaks runner — secret detection in git history."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agent_harness.security.models import AuditFinding


def run_gitleaks(project_dir: Path) -> str | None:
    """Run gitleaks and return JSON output, or None if unavailable.

    Scans full git history. Uses .gitleaksignore for fingerprint-based
    suppression only — no path or regex allowlists.
    """
    try:
        result = subprocess.run(
            [
                "gitleaks",
                "detect",
                "--source",
                str(project_dir),
                "--report-format",
                "json",
                "--report-path",
                "/dev/stdout",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_dir),
            timeout=300,  # 5 min — full history scan can be slow
        )
        # gitleaks exits 1 when leaks found, 0 when clean
        # If stdout is empty and exit code is 0, no leaks
        if result.returncode == 0:
            return "[]"  # No leaks found
        if result.stdout:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def parse_gitleaks_output(output: str) -> list[AuditFinding]:
    """Parse gitleaks JSON output into AuditFindings.

    All gitleaks findings are classified as FAIL — leaked secrets
    are always critical regardless of when they were introduced.
    """
    data = json.loads(output)
    if not isinstance(data, list):
        return []

    findings: list[AuditFinding] = []
    for leak in data:
        # Build a descriptive message
        rule_id = leak.get("RuleID", "unknown-rule")
        file_path = leak.get("File", "unknown")
        commit = leak.get("Commit", "")[:8]
        fingerprint = leak.get("Fingerprint", "")

        description = f"{rule_id} in {file_path}"
        if commit:
            description += f" (commit {commit})"

        findings.append(
            AuditFinding(
                package=file_path,  # Use file path as "package"
                version=commit,  # Use commit hash as "version"
                vuln_id=f"gitleaks:{fingerprint[:16]}"
                if fingerprint
                else f"gitleaks:{rule_id}",
                severity="critical",  # Secrets are always critical
                description=description,
                fix_versions=["rotate secret"],  # Enables FAIL via classify()
                is_new_dep=True,  # Always treat as new so classify() returns FAIL
            )
        )

    return findings
