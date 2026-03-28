"""Security audit orchestrator — detect stacks, run tools, apply policy."""

from __future__ import annotations

from pathlib import Path

from agent_harness.security.config import load_security_config
from agent_harness.security.models import AuditFinding, SecurityReport
from agent_harness.security.gitleaks_scanner import parse_gitleaks_output, run_gitleaks
from agent_harness.security.osv_scanner import parse_osv_output, run_osv_scanner


def run_security_audit(
    project_dir: Path,
    stacks: set[str],
    config: dict,
    *,
    full_history: bool = False,
) -> SecurityReport:
    """Run security audit using osv-scanner and gitleaks."""
    sec_config = load_security_config(config)
    all_findings: list[AuditFinding] = []

    output = run_osv_scanner(project_dir)
    if output is not None:
        all_findings = parse_osv_output(output, sec_config.base_branch, project_dir)

    # Secret detection
    gitleaks_output = run_gitleaks(project_dir, full_history=full_history)
    if gitleaks_output is not None:
        all_findings.extend(parse_gitleaks_output(gitleaks_output))

    return SecurityReport(
        findings=all_findings,
        ignored_ids=sec_config.ignored_cves,
    )
