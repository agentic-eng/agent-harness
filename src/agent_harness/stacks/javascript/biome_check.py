"""
Biome lint and format check.

WHAT: Runs biome lint and biome format on the project.

WHY: Biome is the ruff of JavaScript — a single Rust-based tool for linting and
formatting, ~20x faster than ESLint. Agents generate code with unused variables,
inconsistent formatting, implicit type coercion, and console.log left in
production code. Biome catches all of these in one pass.

WITHOUT IT: Style drift between agent iterations, unused variables accumulate,
console.log ships to production, formatting wars between agent and human edits.

FIX: Run `biome check --fix` to auto-fix, or `agent-harness fix`.

REQUIRES: biome (via PATH or npx fallback)
"""

from pathlib import Path
import shutil

from agent_harness.runner import run_check, CheckResult

# Respect .gitignore via biome's VCS integration — skip dist/, .astro/, node_modules/
BIOME_VCS_FLAGS = [
    "--vcs-enabled=true",
    "--vcs-client-kind=git",
    "--vcs-use-ignore-file=true",
]


def _biome_prefix() -> list[str]:
    """Return biome command prefix — direct if in PATH, npx fallback otherwise."""
    if shutil.which("biome"):
        return ["biome"]
    return ["npx", "@biomejs/biome"]


def run_biome(project_dir: Path) -> list[CheckResult]:
    """Run biome lint and biome format (check mode). Returns list of results."""
    results = []
    prefix = _biome_prefix()

    results.append(
        run_check(
            "biome:lint",
            prefix + ["lint", "."] + BIOME_VCS_FLAGS,
            cwd=str(project_dir),
        )
    )
    results.append(
        run_check(
            "biome:format",
            prefix + ["format", "."] + BIOME_VCS_FLAGS,
            cwd=str(project_dir),
        )
    )
    return results
