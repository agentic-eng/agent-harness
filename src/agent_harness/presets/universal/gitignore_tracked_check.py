"""
Tracked-but-ignored file check.

WHAT: Detects files tracked by git that match .gitignore patterns.

WHY: Adding a pattern to .gitignore only prevents NEW files from being tracked.
Already-tracked files remain in the repository, invisible to developers and agents.
This is the #1 reason .DS_Store, .env backups, and build artifacts linger in repos.

WITHOUT IT: Ignored files silently stay in the repo forever. Public repos ship
OS artifacts (.DS_Store), agents commit files that should be excluded, and
.gitignore gives a false sense of cleanliness.

FIX: Run `git rm --cached <file>` for each offending file, or run `agent-harness fix`.

REQUIRES: git
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from agent_harness.runner import CheckResult


def run_gitignore_tracked(project_dir: Path) -> CheckResult:
    """Check for tracked files that match .gitignore patterns."""
    result = subprocess.run(
        ["git", "ls-files", "-ci", "--exclude-standard"],
        capture_output=True,
        text=True,
        cwd=str(project_dir),
    )
    if result.returncode != 0:
        # Not a git repo or git not available — skip gracefully
        return CheckResult(
            name="gitignore-tracked",
            passed=True,
            output="Not a git repo, skipping",
        )

    files = [f for f in result.stdout.strip().splitlines() if f]
    if not files:
        return CheckResult(
            name="gitignore-tracked",
            passed=True,
            output="No tracked files match .gitignore",
        )

    file_list = "\n  ".join(files)
    return CheckResult(
        name="gitignore-tracked",
        passed=False,
        error=(
            f"Files tracked by git but matching .gitignore:\n  {file_list}\n"
            f"Run: git rm --cached <file>  (or: agent-harness fix)"
        ),
    )
