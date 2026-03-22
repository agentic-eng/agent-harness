from pathlib import Path
import subprocess
from ai_harness.runner import CheckResult


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
