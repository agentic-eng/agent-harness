"""
Conftest package.json check.

WHAT: Runs conftest on package.json with bundled JavaScript policies to enforce
engines field, ESM type, and version hygiene.

WHY: Agents create package.json files missing critical fields (engines, type)
and use wildcard versions. These misconfigurations cause "works on my machine"
failures and non-deterministic dependency resolution.

WITHOUT IT: Node version mismatches in CI/deploy, mixed ESM/CJS module errors,
different dependency versions on every npm install.

FIX: Run `agent-harness audit` to see specific package.json issues.

REQUIRES: conftest (via PATH)
"""
from __future__ import annotations

from pathlib import Path

from agent_harness.runner import CheckResult, run_check

POLICIES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "policies"


def run_conftest_package(project_dir: Path) -> CheckResult:
    """Run conftest on package.json with bundled javascript policies."""
    target = project_dir / "package.json"
    if not target.exists():
        return CheckResult(
            name="conftest-package",
            passed=True,
            output="Skipping conftest-package: package.json not found",
        )
    policy_path = POLICIES_DIR / "javascript"
    cmd = [
        "conftest", "test", str(target),
        "--policy", str(policy_path),
        "--no-color", "--all-namespaces",
    ]
    return run_check("conftest-package", cmd, cwd=str(project_dir))
