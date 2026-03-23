"""
Conftest .gitignore check.

WHAT: Runs conftest on .gitignore with bundled gitignore policies to ensure
secrets and artifacts are excluded from version control, conditional on
detected stacks.

WHY: Agents create .env files with real secrets during development and commit
them. Stack-specific artifacts (.venv, node_modules) bloat the repo. Without
stack awareness, Python entries get flagged on JS projects (false positives)
and JS entries get missed on JS projects (false negatives).

WITHOUT IT: Secrets in git history, false positive noise on wrong stacks,
missing entries for detected stacks.

FIX: Add the reported entries to .gitignore.

REQUIRES: conftest (via PATH)
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from agent_harness.runner import CheckResult, run_check

# Resolve bundled policies relative to this source file.
POLICIES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "policies"


def run_conftest_gitignore(
    project_dir: Path, stacks: set[str] | None = None
) -> CheckResult:
    """Run conftest on .gitignore with stack-conditional policies."""
    target = project_dir / ".gitignore"
    if not target.exists():
        return CheckResult(
            name="conftest-gitignore",
            passed=True,
            output="Skipping conftest-gitignore: .gitignore not found",
        )
    policy_path = POLICIES_DIR / "gitignore"

    # Write stacks data to temp file for conftest --data
    stacks_list = sorted(stacks) if stacks else []
    data_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    )
    json.dump({"stacks": stacks_list}, data_file)
    data_file.close()

    cmd = [
        "conftest",
        "test",
        str(target),
        "--policy",
        str(policy_path),
        "--no-color",
        "--all-namespaces",
        "--data",
        data_file.name,
    ]
    try:
        return run_check("conftest-gitignore", cmd, cwd=str(project_dir))
    finally:
        os.unlink(data_file.name)
