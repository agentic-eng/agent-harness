"""Shared conftest runner for Rego policy checks."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from agent_harness import POLICIES_DIR
from agent_harness.runner import CheckResult, run_check


def run_conftest(
    name: str,
    project_dir: Path,
    target_file: str,
    policy_subdir: str,
    data: dict | None = None,
) -> CheckResult:
    """Run conftest test on a target file with bundled policies."""
    target = project_dir / target_file
    if not target.exists():
        return CheckResult(
            name=name, passed=True, output=f"Skipping {name}: {target_file} not found"
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

    data_path = None
    if data:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(data, tmp)
        tmp.close()
        data_path = tmp.name
        cmd.extend(["--data", data_path])

    try:
        return run_check(name, cmd, cwd=str(project_dir))
    finally:
        if data_path:
            os.unlink(data_path)
