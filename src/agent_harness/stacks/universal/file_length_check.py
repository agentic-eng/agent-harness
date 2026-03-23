"""
File length check.

WHAT: Ensures tracked source files don't exceed extension-specific line limits.

WHY: Agents generate monolith files that grow unboundedly. Long files are harder
to review, harder to test, and agents themselves lose context when editing 1000+
line files. Template-heavy files (.astro, .vue, .svelte) get a higher limit (800)
because HTML markup inflates line counts.

WITHOUT IT: 1000+ line files that no one reviews, circular dependencies from
everything-in-one-module, and agents that lose track of earlier code.

FIX: Split the file into focused modules. Extract classes, helpers, or
components into separate files.

REQUIRES: git (for file listing)
"""
from __future__ import annotations

from pathlib import Path
import subprocess

from agent_harness.runner import CheckResult
from agent_harness.exclusions import is_excluded

DEFAULT_MAX_LINES: dict[str, int] = {
    ".py": 500,
    ".ts": 500,
    ".tsx": 500,
    ".js": 500,
    ".jsx": 500,
    ".astro": 800,
    ".vue": 800,
    ".svelte": 800,
}


def run_file_length(
    project_dir: Path,
    max_lines_override: dict[str, int] | None = None,
    exclude_patterns: list[str] | None = None,
) -> CheckResult:
    """Check tracked source files against extension-specific line limits."""
    thresholds = {**DEFAULT_MAX_LINES, **(max_lines_override or {})}

    extensions = list(thresholds.keys())
    git_patterns = [f"*{ext}" for ext in extensions]
    result = subprocess.run(
        ["git", "ls-files"] + git_patterns,
        capture_output=True, text=True, cwd=str(project_dir)
    )
    files = [f for f in result.stdout.strip().splitlines() if f]

    if exclude_patterns:
        files = [f for f in files if not is_excluded(f, exclude_patterns)]

    if not files:
        return CheckResult(name="file-length", passed=True, output="No tracked source files to check")

    errors = []
    for f in files:
        path = project_dir / f
        if not path.exists():
            continue
        ext = path.suffix
        max_lines = thresholds.get(ext)
        if max_lines is None:
            continue
        lines = len(path.read_text().splitlines())
        if lines > max_lines:
            errors.append(f"{f}: {lines} lines (max {max_lines} for {ext})")

    if errors:
        return CheckResult(name="file-length", passed=False, error="\n".join(errors))
    return CheckResult(
        name="file-length",
        passed=True,
        output=f"All {len(files)} files within extension-specific limits",
    )
