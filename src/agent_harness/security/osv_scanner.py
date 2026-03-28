"""OSV-Scanner runner — single tool for all ecosystem vulnerability scanning."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agent_harness.security.models import AuditFinding

# Lockfiles that osv-scanner can read
LOCKFILES = ["uv.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"]


def run_osv_scanner(project_dir: Path) -> str | None:
    """Run osv-scanner and return JSON output, or None if unavailable."""
    # Find which lockfiles exist
    lockfile_args = []
    for lockfile in LOCKFILES:
        if (project_dir / lockfile).exists():
            lockfile_args.extend(["--lockfile", str(project_dir / lockfile)])

    if not lockfile_args:
        return None

    try:
        result = subprocess.run(
            ["osv-scanner", "--format", "json", *lockfile_args],
            capture_output=True,
            text=True,
            cwd=str(project_dir),
            timeout=120,
        )
        # osv-scanner exits 1 when vulns found — that's expected
        if result.stdout:
            return result.stdout
        if result.returncode not in (0, 1):
            import click

            click.echo(
                f"  WARN  osv-scanner failed (exit {result.returncode})", err=True
            )
            if result.stderr:
                click.echo(f"         {result.stderr.strip()[:200]}", err=True)
    except FileNotFoundError:
        import click

        click.echo(
            "  SKIP  osv-scanner not installed (brew install osv-scanner)", err=True
        )
    except subprocess.TimeoutExpired:
        import click

        click.echo("  WARN  osv-scanner timed out after 120s", err=True)
    return None


def _extract_severity(vuln: dict) -> str:
    """Extract severity label from OSV vulnerability data."""
    # Try database_specific.severity first (already a label)
    db_specific = vuln.get("database_specific", {})
    if isinstance(db_specific, dict):
        sev = db_specific.get("severity")
        if isinstance(sev, str):
            return sev.lower()

    # Try CVSS score
    for sev_entry in vuln.get("severity", []):
        score_str = sev_entry.get("score", "")
        if "CVSS" in score_str:
            # Extract base score from CVSS vector or numeric score
            # Try numeric first
            try:
                score = float(score_str)
            except ValueError:
                # Parse from vector string — last component or use baseScore
                # CVSS:3.1/AV:N/AC:L/... doesn't contain the numeric score
                # in the vector itself, but some outputs include it separately
                continue
            if score >= 9.0:
                return "critical"
            if score >= 7.0:
                return "high"
            if score >= 4.0:
                return "medium"
            return "low"

    return "unknown"


def _get_fix_versions(vuln: dict) -> list[str]:
    """Extract fix versions from vulnerability data."""
    versions = []
    for affected in vuln.get("affected", []):
        for range_entry in affected.get("ranges", []):
            for event in range_entry.get("events", []):
                if "fixed" in event:
                    versions.append(event["fixed"])
    return versions


def is_new_package(package_name: str, base_branch: str, project_dir: Path) -> bool:
    """Check if a package is new (not in the base branch's lockfiles).

    Searches for the quoted package name to avoid substring matches
    (e.g., "requests" matching "requests-toolbelt"). Lockfiles always
    quote package names: uv.lock uses `name = "pkg"`, package-lock.json
    uses `"pkg":` as a key.
    """
    quoted_name = f'"{package_name.lower()}"'
    for lockfile in LOCKFILES:
        result = subprocess.run(
            ["git", "show", f"{base_branch}:{lockfile}"],
            capture_output=True,
            text=True,
            cwd=str(project_dir),
        )
        if result.returncode == 0 and quoted_name in result.stdout.lower():
            return False
    return True


def parse_osv_output(
    output: str, base_branch: str, project_dir: Path
) -> list[AuditFinding]:
    """Parse osv-scanner JSON output into AuditFindings."""
    data = json.loads(output)
    findings: list[AuditFinding] = []

    for result in data.get("results", []):
        for pkg_entry in result.get("packages", []):
            pkg_info = pkg_entry.get("package", {})
            pkg_name = pkg_info.get("name", "")
            pkg_version = pkg_info.get("version", "")
            is_new = is_new_package(pkg_name, base_branch, project_dir)

            for vuln in pkg_entry.get("vulnerabilities", []):
                findings.append(
                    AuditFinding(
                        package=pkg_name,
                        version=pkg_version,
                        vuln_id=vuln.get("id", ""),
                        severity=_extract_severity(vuln),
                        description=vuln.get("summary", ""),
                        fix_versions=_get_fix_versions(vuln),
                        is_new_dep=is_new,
                    )
                )

    return findings
