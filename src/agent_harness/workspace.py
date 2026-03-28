"""Workspace discovery — finds all project roots in a repo tree."""

from __future__ import annotations

from pathlib import Path

from agent_harness.git_files import find_files


def discover_roots(project_dir: Path) -> list[Path]:
    """Find directories containing .agent-harness.yml."""
    files = find_files(project_dir, ["**/.agent-harness.yml", ".agent-harness.yml"])
    return sorted({f.parent for f in files})
