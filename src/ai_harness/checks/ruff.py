from pathlib import Path
from ai_harness.runner import run_check, CheckResult
import shutil


def run_ruff(project_dir: Path) -> list[CheckResult]:
    """Run ruff format --check and ruff check. Returns list of results."""
    results = []
    if shutil.which("ruff"):
        results.append(run_check("ruff:format", ["ruff", "format", "--check"], cwd=str(project_dir)))
        results.append(run_check("ruff:check", ["ruff", "check"], cwd=str(project_dir)))
    else:
        results.append(run_check("ruff:format", ["uv", "run", "ruff", "format", "--check"], cwd=str(project_dir)))
        results.append(run_check("ruff:check", ["uv", "run", "ruff", "check"], cwd=str(project_dir)))
    return results
