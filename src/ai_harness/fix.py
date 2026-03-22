from pathlib import Path
from ai_harness.runner import run_check
import shutil


def run_fix(project_dir: Path) -> list[str]:
    """Auto-fix what's fixable, then return actions taken."""
    actions = []

    if shutil.which("ruff"):
        fix_cmd = ["ruff", "check", "--fix"]
        fmt_cmd = ["ruff", "format"]
    else:
        fix_cmd = ["uv", "run", "ruff", "check", "--fix"]
        fmt_cmd = ["uv", "run", "ruff", "format"]

    # Ruff fix
    result = run_check("ruff:fix", fix_cmd, cwd=str(project_dir))
    if result.passed:
        actions.append("ruff: auto-fixed lint issues")
    elif "not found" in result.error.lower():
        actions.append("ruff: not installed, skipping fix")

    # Ruff format
    result = run_check("ruff:format", fmt_cmd, cwd=str(project_dir))
    if result.passed:
        actions.append("ruff: formatted code")
    elif "not found" in result.error.lower():
        actions.append("ruff: not installed, skipping format")

    return actions
