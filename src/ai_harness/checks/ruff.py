from pathlib import Path
from ai_harness.runner import run_check, CheckResult


def run_ruff(project_dir: Path) -> list[CheckResult]:
    """Run ruff format --check and ruff check. Returns list of results."""
    results = []
    results.append(run_check("ruff:format", ["ruff", "format", "--check"], cwd=str(project_dir)))
    results.append(run_check("ruff:check", ["ruff", "check"], cwd=str(project_dir)))
    return results
