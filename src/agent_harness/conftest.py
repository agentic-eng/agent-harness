"""Shared conftest runner for Rego policy checks."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from agent_harness import POLICIES_DIR
from agent_harness.runner import CheckResult, _resolve_tool, run_check


@dataclass
class DiagnosticResult:
    name: str
    target_file: str
    critical: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    passed: bool = True


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


def run_conftest_diagnostic(
    name: str,
    project_dir: Path,
    target_file: str,
    policy_subdir: str,
    data: dict | None = None,
) -> DiagnosticResult:
    """Run conftest with JSON output, parse into critical/recommendation."""
    target = project_dir / target_file
    if not target.exists():
        return DiagnosticResult(name=name, target_file=target_file, passed=True)

    resolved = _resolve_tool("conftest", cwd=str(project_dir))
    if not resolved:
        return DiagnosticResult(
            name=name,
            target_file=target_file,
            critical=["conftest not found — not installed or not in PATH"],
            passed=False,
        )

    policy_path = POLICIES_DIR / policy_subdir
    cmd = [
        resolved,
        "test",
        str(target),
        "--policy",
        str(policy_path),
        "--no-color",
        "--all-namespaces",
        "--output",
        "json",
    ]

    data_path = None
    if data:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(data, tmp)
        tmp.close()
        data_path = tmp.name
        cmd.extend(["--data", data_path])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(project_dir), timeout=60
        )
    except Exception as exc:
        return DiagnosticResult(
            name=name,
            target_file=target_file,
            critical=[f"conftest failed to run: {exc}"],
            passed=False,
        )
    finally:
        if data_path:
            os.unlink(data_path)

    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return DiagnosticResult(
            name=name,
            target_file=target_file,
            critical=[f"conftest output could not be parsed as JSON: {exc}"],
            passed=False,
        )

    critical: list[str] = []
    recommendations: list[str] = []
    for entry in parsed:
        for failure in entry.get("failures", []) or []:
            critical.append(failure["msg"])
        for warning in entry.get("warnings", []) or []:
            recommendations.append(warning["msg"])

    return DiagnosticResult(
        name=name,
        target_file=target_file,
        critical=critical,
        recommendations=recommendations,
        passed=len(critical) == 0,
    )
