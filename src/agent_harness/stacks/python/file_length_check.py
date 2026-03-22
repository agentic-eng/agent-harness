"""
Python file length check.

WHAT: Ensures no Python file exceeds a configurable line count (default 500).

WHY: Agents generate monolith files — all logic in one module that grows
unboundedly. Long files are harder to review, harder to test, and agents
themselves lose context when editing 1000+ line files. A length limit forces
decomposition into focused modules.

WITHOUT IT: 1000+ line files that no one reviews, circular dependencies from
everything-in-one-module, and agents that lose track of earlier code in the
same file.

FIX: Split the file into focused modules. Extract classes, helpers, or
route groups into separate files.

REQUIRES: git (for file listing)
"""
from pathlib import Path
import subprocess

from agent_harness.runner import CheckResult


def run_file_length(project_dir: Path, max_lines: int = 500) -> CheckResult:
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        capture_output=True, text=True, cwd=str(project_dir)
    )
    py_files = [f for f in result.stdout.strip().splitlines() if f]
    if not py_files:
        return CheckResult(name="file-length", passed=True, output="No Python files, skipping")

    errors = []
    for f in py_files:
        path = project_dir / f
        if path.exists():
            lines = len(path.read_text().splitlines())
            if lines > max_lines:
                errors.append(f"{f}: {lines} lines (max {max_lines})")

    if errors:
        return CheckResult(name="file-length", passed=False, error="\n".join(errors))
    return CheckResult(name="file-length", passed=True, output=f"All {len(py_files)} files under {max_lines} lines")
