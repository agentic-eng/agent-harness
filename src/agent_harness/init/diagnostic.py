"""Diagnostic display for init command."""

from __future__ import annotations

from pathlib import Path

import click

from agent_harness.preset import ToolInfo
from agent_harness.runner import tool_available
from agent_harness.setup import SetupIssue


def display_setup_issues(
    preset_name: str,
    issues: list[SetupIssue],
    tools: list[ToolInfo],
    project_dir: Path,
) -> tuple[int, int, int]:
    """Display setup check results. Returns (critical_count, recommendation_count, fixable_count)."""
    click.echo(f"\n  {preset_name}:")

    critical_count = 0
    recommendation_count = 0
    fixable_count = 0

    for issue in issues:
        if issue.severity == "critical":
            suffix = " (fixable)" if issue.fixable else ""
            click.echo(f"    \u2717 {issue.file}: {issue.message}    critical{suffix}")
            critical_count += 1
            if issue.fixable:
                fixable_count += 1
        else:
            click.echo(f"    ~ {issue.file}: {issue.message}    recommendation")
            recommendation_count += 1

    for tool in tools:
        available = tool_available(tool.binary, project_dir)
        if available:
            click.echo(f"    \u2713 {tool.name} installed")
        else:
            click.echo(f"    \u2717 {tool.name} not installed    ({tool.install_hint})")
            critical_count += 1

    return critical_count, recommendation_count, fixable_count


def display_summary(
    critical: int, recommendations: int, fixable: int, missing_files: int
) -> None:
    """Display final summary line."""
    parts = []
    if critical:
        fix_note = f" ({fixable} fixable)" if fixable else ""
        parts.append(f"{critical} critical{fix_note}")
    if recommendations:
        parts.append(
            f"{recommendations} recommendation{'s' if recommendations != 1 else ''}"
        )
    if missing_files:
        parts.append(
            f"{missing_files} file{'s' if missing_files != 1 else ''} to create"
        )

    if parts:
        click.echo(f"\n  {', '.join(parts)}.")
    else:
        click.echo("\n  All checks passed.")
