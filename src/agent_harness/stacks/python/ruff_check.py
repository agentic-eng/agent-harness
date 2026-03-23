"""
Ruff format and lint check.

WHAT: Runs ruff format --check and ruff check on the project.

WHY: Ruff is the fastest Python linter. Agents generate code that violates style
rules, uses deprecated patterns, and leaves unused imports. Without ruff in the
loop, agents accumulate style debt with every iteration.

WITHOUT IT: Import ordering drifts, dead code accumulates, agents reformat
inconsistently between iterations, print() debug statements ship to production.

FIX: Run `agent-harness fix` — auto-runs ruff check --fix and ruff format.

REQUIRES: ruff (via PATH or uv run fallback)
"""

from pathlib import Path

from agent_harness.runner import run_check, CheckResult
import shutil


def run_ruff(project_dir: Path) -> list[CheckResult]:
    """Run ruff format --check and ruff check. Returns list of results."""
    results = []
    if shutil.which("ruff"):
        results.append(
            run_check(
                "ruff:format", ["ruff", "format", "--check"], cwd=str(project_dir)
            )
        )
        results.append(run_check("ruff:check", ["ruff", "check"], cwd=str(project_dir)))
    else:
        results.append(
            run_check(
                "ruff:format",
                ["uv", "run", "ruff", "format", "--check"],
                cwd=str(project_dir),
            )
        )
        results.append(
            run_check(
                "ruff:check", ["uv", "run", "ruff", "check"], cwd=str(project_dir)
            )
        )
    return results
