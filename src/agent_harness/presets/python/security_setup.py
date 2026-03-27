"""Python security setup check — verify pip-audit is available."""

from __future__ import annotations

import tomllib
from pathlib import Path

from agent_harness.setup_check import SetupIssue


def check_python_security_setup(project_dir: Path) -> list[SetupIssue]:
    """Check that pip-audit is in dev dependencies."""
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return []

    data = tomllib.loads(pyproject_path.read_text())

    all_dev_deps: list[str] = []

    for group_deps in data.get("dependency-groups", {}).values():
        for dep in group_deps:
            if isinstance(dep, str):
                all_dev_deps.append(dep.lower())

    for group_deps in data.get("project", {}).get("optional-dependencies", {}).values():
        for dep in group_deps:
            all_dev_deps.append(dep.lower())

    has_pip_audit = any("pip-audit" in dep for dep in all_dev_deps)

    if not has_pip_audit:
        return [
            SetupIssue(
                file="pyproject.toml",
                message="pip-audit not in dev dependencies — add for security auditing",
                severity="recommendation",
            )
        ]

    return []
