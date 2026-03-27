"""Security audit display formatting."""

from __future__ import annotations

from agent_harness.security.models import Classification, SecurityReport


def format_report(report: SecurityReport) -> list[str]:
    """Format a SecurityReport as human-readable lines."""
    lines: list[str] = []

    if not report.findings:
        lines.append("  No vulnerabilities found.")
        return lines

    fails: list[str] = []
    warns: list[str] = []
    ignored_lines: list[str] = []

    for finding in report.findings:
        if finding.vuln_id in report.ignored_ids:
            ignored_lines.append(
                f"  SKIP  {finding.package} {finding.vuln_id} (ignored)"
            )
            continue

        classification = finding.classify()
        fix_info = (
            f" → fix: {', '.join(finding.fix_versions)}"
            if finding.fix_versions
            else " (no fix)"
        )
        new_tag = " [NEW]" if finding.is_new_dep else ""
        line = (
            f"  {finding.package}@{finding.version}{new_tag} "
            f"{finding.vuln_id} ({finding.severity}){fix_info}"
        )

        if classification == Classification.FAIL:
            fails.append(f"  FAIL  {line.strip()}")
        else:
            warns.append(f"  WARN  {line.strip()}")

    for line in fails:
        lines.append(line)
    for line in warns:
        lines.append(line)
    for line in ignored_lines:
        lines.append(line)

    summary_parts = []
    if report.fail_count:
        summary_parts.append(f"{report.fail_count} blocked")
    if report.warn_count:
        summary_parts.append(f"{report.warn_count} warnings")
    if report.ignored_count:
        summary_parts.append(f"{report.ignored_count} ignored")
    lines.append(f"\n  {', '.join(summary_parts)}")

    return lines
