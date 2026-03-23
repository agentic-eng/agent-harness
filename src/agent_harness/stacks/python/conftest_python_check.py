"""
Conftest pyproject.toml check.

WHAT: Runs conftest on pyproject.toml with bundled Python policies to enforce
pytest config, ruff config, coverage settings, and test isolation.

WHY: Agents misconfigure pytest (missing strict-markers, no coverage), ruff
(verbose output format, short line-length), and skip test isolation (no
pytest-env, tests hit production DB). These misconfigurations compound silently
over iterations.

WITHOUT IT: Phantom test markers that select nothing, opaque dot-based test
output, coverage gaps discovered only in CI, and tests accidentally running
against production databases.

FIX: Run `agent-harness audit` to see specific pyproject.toml issues and
their fixes.

REQUIRES: conftest (via PATH)
"""

from __future__ import annotations

from pathlib import Path

from agent_harness.runner import CheckResult, run_check

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


def run_conftest_python(project_dir: Path) -> CheckResult:
    """Run conftest on pyproject.toml with bundled python policies."""
    return _run_conftest(
        "conftest-python",
        project_dir,
        "pyproject.toml",
        "python",
    )
