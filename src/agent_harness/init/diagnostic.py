"""Diagnostic display for init command."""

from __future__ import annotations

from pathlib import Path

import click

from agent_harness.conftest import DiagnosticResult
from agent_harness.preset import ToolInfo
from agent_harness.runner import tool_available


def display_diagnostics(
    preset_name: str,
    diagnostics: list[DiagnosticResult],
    tools: list[ToolInfo],
    project_dir: Path,
) -> tuple[int, int]:
    """Display diagnostic results for a preset. Returns (critical_count, recommendation_count)."""
    click.echo(f"\n  Scanning {preset_name}...")

    critical_count = 0
    recommendation_count = 0

    for diag in diagnostics:
        for msg in diag.critical:
            click.echo(f"    \u2717 {diag.target_file}: {msg}    critical")
            critical_count += 1
        for msg in diag.recommendations:
            click.echo(f"    ~ {diag.target_file}: {msg}    recommendation")
            recommendation_count += 1

    for tool in tools:
        available = tool_available(tool.binary, project_dir)
        if available:
            click.echo(f"    \u2713 {tool.name} installed")
        else:
            click.echo(f"    \u2717 {tool.name} not installed    ({tool.install_hint})")
            critical_count += 1

    return critical_count, recommendation_count


def display_summary(critical: int, recommendations: int, missing_files: int) -> None:
    """Display final summary line."""
    parts = []
    if critical:
        parts.append(f"{critical} critical")
    if recommendations:
        parts.append(f"{recommendations} recommendation{'s' if recommendations != 1 else ''}")
    if missing_files:
        parts.append(f"{missing_files} file{'s' if missing_files != 1 else ''} to create")

    if parts:
        click.echo(f"\n  {', '.join(parts)}.")
    else:
        click.echo("\n  All checks passed.")
