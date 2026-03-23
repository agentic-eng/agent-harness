"""
Conftest JSON validation check.

WHAT: Validates all git-tracked JSON files by parsing them with conftest.

WHY: Agents generate and edit JSON files (package.json, tsconfig, config files)
and frequently produce invalid JSON — trailing commas, missing brackets, encoding
issues. Invalid JSON causes silent failures in tools that read these files.

WITHOUT IT: Broken JSON files ship to production. Build tools, config parsers,
and deployment scripts fail with cryptic parse errors instead of catching the
problem at lint time.

FIX: Fix the JSON syntax error reported in the output. Most editors have
JSON validation built in.

REQUIRES: conftest (via PATH)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from agent_harness.exclusions import is_excluded
from agent_harness.runner import CheckResult, run_check

JSONC_FILES = {"tsconfig.json", "jsconfig.json"}
JSONC_DIRS = {".vscode"}


def _is_jsonc(filepath: str) -> bool:
    """Check if a JSON file is actually JSONC (JSON with comments)."""
    basename = filepath.split("/")[-1]
    if basename in JSONC_FILES:
        return True
    parts = filepath.split("/")
    return any(d in JSONC_DIRS for d in parts[:-1])


def run_conftest_json(
    project_dir: Path, exclude_patterns: list[str] | None = None
) -> CheckResult:
    """Validate JSON files via conftest parse --parser json."""
    name = "conftest-json"
    try:
        result = subprocess.run(
            ["git", "ls-files", "*.json", "**/*.json"],
            capture_output=True,
            text=True,
            cwd=str(project_dir),
            timeout=10,
        )
        json_files = [f for f in result.stdout.strip().splitlines() if f]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        json_files = []

    # Filter JSONC and excluded files
    json_files = [f for f in json_files if not _is_jsonc(f)]
    if exclude_patterns:
        json_files = [f for f in json_files if not is_excluded(f, exclude_patterns)]

    if not json_files:
        return CheckResult(
            name=name,
            passed=True,
            output="Skipping conftest-json: no JSON files found",
        )

    errors: list[str] = []
    for jf in json_files:
        cmd = ["conftest", "parse", "--parser", "json", str(project_dir / jf)]
        cr = run_check(f"{name}:{jf}", cmd, cwd=str(project_dir))
        if not cr.passed:
            errors.append(f"{jf}: {cr.error or cr.output}")

    if errors:
        return CheckResult(
            name=name,
            passed=False,
            error="\n".join(errors),
        )
    return CheckResult(
        name=name,
        passed=True,
        output=f"All {len(json_files)} JSON file(s) valid",
    )
