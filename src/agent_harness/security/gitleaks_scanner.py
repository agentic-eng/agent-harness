"""Gitleaks runner — secret detection in git history."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agent_harness.security.models import AuditFinding


def run_gitleaks(project_dir: Path, *, full_history: bool = False) -> str | None:
    """Run gitleaks and return JSON output, or None if unavailable.

    By default scans working directory only (--no-git, fast).
    With full_history=True, scans full git history (slow, catches deleted secrets).
    Uses .gitleaksignore for fingerprint-based suppression only.
    """
    cmd = [
        "gitleaks",
        "detect",
        "--source",
        str(project_dir),
        "--report-format",
        "json",
        "--report-path",
        "/dev/stdout",
    ]
    if not full_history:
        cmd.append("--no-git")

    timeout = 300 if full_history else 60

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(project_dir),
            timeout=timeout,
        )
        # gitleaks exits 1 when leaks found, 0 when clean
        if result.returncode == 0:
            return "[]"  # No leaks found
        if result.returncode == 1 and result.stdout:
            return result.stdout
        if result.returncode > 1:
            import click

            click.echo(f"  WARN  gitleaks failed (exit {result.returncode})", err=True)
            if result.stderr:
                click.echo(f"         {result.stderr.strip()[:200]}", err=True)
    except FileNotFoundError:
        import click

        click.echo("  SKIP  gitleaks not installed (brew install gitleaks)", err=True)
    except subprocess.TimeoutExpired:
        import click

        click.echo("  WARN  gitleaks timed out after 300s", err=True)
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
                fix_versions=[],
                always_fail=True,  # Secrets always block — no WARN
            )
        )

    return findings
