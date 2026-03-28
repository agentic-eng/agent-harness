"""
Hadolint Dockerfile linter check.

WHAT: Runs hadolint on all Dockerfiles in the project tree.

WHY: Hadolint is a Dockerfile-specific linter that catches best-practice
violations (DL/SC rules) that conftest policies don't cover.

WITHOUT IT: Subtle Dockerfile anti-patterns accumulate.

FIX: Read hadolint's rule output (DLxxxx / SCxxxx) and apply the suggested fix.

REQUIRES: hadolint (via PATH)
"""

from __future__ import annotations

from pathlib import Path

from agent_harness.runner import CheckResult, run_check


def run_hadolint(
    project_dir: Path, dockerfiles: list[Path] | None = None
) -> list[CheckResult]:
    """Run hadolint on discovered Dockerfiles. Returns one result per file."""
    if dockerfiles is None:
        dockerfile = project_dir / "Dockerfile"
        if not dockerfile.exists():
            return [
                CheckResult(
                    name="hadolint", passed=True, output="No Dockerfile, skipping"
                )
            ]
        return [
            run_check("hadolint", ["hadolint", str(dockerfile)], cwd=str(project_dir))
        ]

    if not dockerfiles:
        return [
            CheckResult(name="hadolint", passed=True, output="No Dockerfiles found")
        ]

    results = []
    for rel_path in dockerfiles:
        abs_path = project_dir / rel_path
        name = f"hadolint:{rel_path}" if str(rel_path) != "Dockerfile" else "hadolint"
        results.append(
            run_check(name, ["hadolint", str(abs_path)], cwd=str(project_dir))
        )
    return results
