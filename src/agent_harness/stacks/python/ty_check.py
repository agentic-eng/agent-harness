"""
Ty type checker.

WHAT: Runs ty check on the project for type error detection.

WHY: Agents generate code with type mismatches — wrong argument types, missing
return annotations, incompatible assignments. Type checking catches a class of
bugs that linting and tests miss: structural errors in how functions compose.

WITHOUT IT: Runtime TypeErrors in production, silent data corruption from wrong
argument types, and APIs that accept Any when they should be strict.

FIX: Fix the type errors reported by ty. Add type annotations to function
signatures and fix incompatible assignments.

REQUIRES: ty (via PATH or uv run fallback)
"""

from pathlib import Path

from agent_harness.runner import run_check, CheckResult
import shutil


def run_ty(project_dir: Path) -> CheckResult:
    """Run ty type checker. Falls back to uv run ty if ty not in PATH."""
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        return CheckResult(name="ty", passed=True, output="No pyproject.toml, skipping")
    if shutil.which("ty"):
        return run_check("ty", ["ty", "check"], cwd=str(project_dir))
    return run_check("ty", ["uv", "run", "ty", "check"], cwd=str(project_dir))
