from pathlib import Path
from agent_harness.config import load_config
from agent_harness.runner import run_check
import shutil


def run_fix(project_dir: Path) -> list[str]:
    """Auto-fix what's fixable, then return actions taken."""
    actions = []
    config = load_config(project_dir)

    # Python: ruff fix
    if "python" in config.stacks:
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

    # JavaScript: biome fix
    if "javascript" in config.stacks:
        from agent_harness.stacks.javascript.biome_check import (
            _biome_prefix,
            BIOME_VCS_FLAGS,
        )

        biome_cmd = _biome_prefix() + ["check", "--fix", "."] + BIOME_VCS_FLAGS

        result = run_check("biome:fix", biome_cmd, cwd=str(project_dir))
        if result.passed:
            actions.append("biome: auto-fixed lint and format issues")
        elif "not found" in result.error.lower():
            actions.append("biome: not installed, skipping fix")

    return actions
