"""
Hadolint Dockerfile linter check.

WHAT: Runs hadolint on the project Dockerfile.

WHY: Hadolint is a Dockerfile-specific linter that catches best-practice
violations (DL/SC rules) that conftest policies don't cover — apt-get without
--no-install-recommends, missing cleanup in the same layer, shell form vs exec
form, and dozens more. It's the shellcheck equivalent for Dockerfiles.

WITHOUT IT: Subtle Dockerfile anti-patterns accumulate: bloated images from
missing cleanup, security issues from shell form CMD, and non-reproducible
builds from unpinned apt packages.

FIX: Read hadolint's rule output (DLxxxx / SCxxxx) and apply the suggested fix.
Most rules have a --ignore flag if intentionally skipped.

REQUIRES: hadolint (via PATH)
"""

from pathlib import Path

from agent_harness.runner import run_check, CheckResult


def run_hadolint(project_dir: Path) -> CheckResult:
    dockerfile = project_dir / "Dockerfile"
    if not dockerfile.exists():
        return CheckResult(
            name="hadolint", passed=True, output="No Dockerfile, skipping"
        )
    return run_check("hadolint", ["hadolint", str(dockerfile)], cwd=str(project_dir))
