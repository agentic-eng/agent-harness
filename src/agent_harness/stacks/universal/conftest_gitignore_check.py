"""
Conftest .gitignore check.

WHAT: Runs conftest on .gitignore with bundled gitignore policies to ensure
secrets and artifacts are excluded from version control.

WHY: Agents create .env files with real secrets during development and commit
them. .venv and __pycache__ bloat the repo and slow git operations. Once secrets
are in git history, they require history rewriting to remove.

WITHOUT IT: Secrets in git history (extractable forever), 500MB repos from
committed venvs, and slow clones on every CI run.

FIX: Add .env, .venv, and __pycache__ to .gitignore.

REQUIRES: conftest (via PATH)
"""
from __future__ import annotations

from pathlib import Path

from agent_harness.runner import CheckResult, run_check

# Resolve bundled policies relative to this source file.
POLICIES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "policies"


def _run_conftest(
    name: str,
    project_dir: Path,
    target_file: str,
    policy_subdir: str,
) -> CheckResult:
    """Run conftest test on a target file with policies from a subdirectory."""
    target = project_dir / target_file
    if not target.exists():
        return CheckResult(
            name=name,
            passed=True,
            output=f"Skipping {name}: {target_file} not found",
        )
    policy_path = POLICIES_DIR / policy_subdir
    cmd = [
        "conftest",
        "test",
        str(target),
        "--policy",
        str(policy_path),
        "--no-color",
        "--all-namespaces",
    ]
    return run_check(name, cmd, cwd=str(project_dir))


def run_conftest_gitignore(project_dir: Path) -> CheckResult:
    """Run conftest on .gitignore with bundled gitignore policies."""
    return _run_conftest(
        "conftest-gitignore",
        project_dir,
        ".gitignore",
        "gitignore",
    )
