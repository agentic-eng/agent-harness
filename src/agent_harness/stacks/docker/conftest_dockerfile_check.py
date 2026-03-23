"""
Conftest Dockerfile check.

WHAT: Runs conftest on Dockerfile with bundled policies covering base image
selection, cache mounts, healthchecks, layer ordering, secrets, and non-root user.

WHY: Agents generate Dockerfiles that run as root, skip healthchecks, use Alpine
with musl-sensitive stacks, hardcode secrets in ENV/ARG, and bust cache by copying
source before dependencies. Each of these is a production incident waiting to happen.

WITHOUT IT: Containers run as root (one exploit = host compromise), orchestrators
can't detect unhealthy containers, 5-minute builds that should take 10 seconds,
and secrets leaked in image layers.

FIX: Read the specific conftest violation messages — each maps to a concrete
Dockerfile change (add USER, add HEALTHCHECK, reorder COPY layers, etc.).

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


def run_conftest_dockerfile(project_dir: Path) -> CheckResult:
    """Run conftest on Dockerfile with bundled dockerfile policies."""
    return _run_conftest(
        "conftest-dockerfile",
        project_dir,
        "Dockerfile",
        "dockerfile",
    )
