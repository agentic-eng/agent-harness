"""Stack detection orchestrator — delegates to preset detect methods."""

from __future__ import annotations

from pathlib import Path

from agent_harness.registry import PRESETS

_SKIP_DIRS = {
    ".venv",
    "venv",
    "node_modules",
    ".git",
    "dist",
    "build",
    "__pycache__",
    ".astro",
    ".next",
    ".nuxt",
    ".worktrees",
    "_archive",
    ".pytest_cache",
    ".ruff_cache",
}


def detect_stacks(project_dir: Path) -> set[str]:
    """Detect which stacks a project uses based on file presence."""
    return {p.name for p in PRESETS if p.detect(project_dir)}


def detect_all(project_dir: Path, max_depth: int = 4) -> dict[Path, set[str]]:
    """Detect stacks in root and subdirectories. Returns {path: stacks}."""
    results: dict[Path, set[str]] = {}
    _detect_recursive(project_dir, results, depth=0, max_depth=max_depth)
    return results


def _detect_recursive(
    directory: Path, results: dict, depth: int, max_depth: int
) -> None:
    if depth > max_depth:
        return
    stacks = detect_stacks(directory)
    if stacks:
        results[directory] = stacks
    try:
        children = sorted(directory.iterdir())
    except PermissionError:
        return
    for child in children:
        if (
            child.is_dir()
            and child.name not in _SKIP_DIRS
            and not child.name.startswith(".")
        ):
            _detect_recursive(child, results, depth + 1, max_depth)
