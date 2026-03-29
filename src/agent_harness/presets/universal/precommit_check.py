"""
Pre-commit hooks installation check.

WHAT: Verifies that pre-commit hooks are installed when a
.pre-commit-config.yaml exists in the project.

WHY: Without installed hooks, agents can commit freely without any gate
running. Having a config file without hooks installed is a false sense
of security — the gate exists on paper but never fires.

WITHOUT IT: Agents bypass linting entirely by committing directly.
Type checkers, formatters, and policy checks never run, and broken
code ships to the repo.

FIX: Run `prek install` or `pre-commit install` to activate hooks.

REQUIRES: git
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from agent_harness.runner import CheckResult


def _resolve_hooks_dir(git_root: Path) -> Path:
    """Find the git hooks directory, respecting core.hooksPath."""
    result = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
        cwd=str(git_root),
    )
    if result.returncode == 0 and result.stdout.strip():
        hooks_path = Path(result.stdout.strip())
        if hooks_path.is_absolute():
            return hooks_path
        return git_root / hooks_path
    return git_root / ".git" / "hooks"


def run_precommit_check(project_dir: Path, git_root: Path | None = None) -> CheckResult:
    """Check that pre-commit hooks are installed if config exists."""
    import os

    if os.environ.get("CI"):
        return CheckResult(
            name="precommit-hooks",
            passed=True,
            output="Skipping in CI — CI is the quality gate",
        )

    check_dir = git_root if git_root else project_dir

    config_path = check_dir / ".pre-commit-config.yaml"
    if not config_path.exists():
        return CheckResult(
            name="precommit-hooks",
            passed=True,
            output="No .pre-commit-config.yaml found, skipping",
        )

    hooks_dir = _resolve_hooks_dir(check_dir)
    hook_path = hooks_dir / "pre-commit"
    if not hook_path.exists():
        return CheckResult(
            name="precommit-hooks",
            passed=False,
            error=(
                "Pre-commit hooks not installed.\n"
                ".pre-commit-config.yaml exists but no pre-commit hook found.\n"
                "Run: prek install  (or: pre-commit install)"
            ),
        )

    return CheckResult(
        name="precommit-hooks",
        passed=True,
        output="Pre-commit hooks installed",
    )
