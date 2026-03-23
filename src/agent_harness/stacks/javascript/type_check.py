"""
Framework-aware TypeScript type checking.

WHAT: Runs the best available type checker for the detected JS framework.
Astro → `astro check`. Next.js → `next lint`. Default → `tsc --noEmit`.

WHY: Framework-specific type checkers understand their own file types (.astro,
.vue) and catch errors that plain tsc misses. Agents generate components with
wrong prop types, missing imports, and broken content collection schemas.
Framework checkers catch these; tsc alone does not.

WITHOUT IT: Type errors in .astro/.vue files go undetected, broken component
props ship silently, content collection schema violations only surface at build.

FIX: Fix the type errors reported. For Astro, see https://docs.astro.build/en/guides/typescript/

REQUIRES: Framework CLI (astro, next) or tsc, via PATH or npx fallback
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil

from agent_harness.runner import run_check, CheckResult

FRAMEWORK_DEPS = {
    "astro": "astro",
    "next": "next",
    # "nuxt": "nuxt",  # TODO: add nuxi typecheck support
}


def detect_framework(project_dir: Path) -> str | None:
    """Detect JS framework from package.json dependencies."""
    pkg_path = project_dir / "package.json"
    if not pkg_path.exists():
        return None
    try:
        pkg = json.loads(pkg_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    for dep, framework in FRAMEWORK_DEPS.items():
        if dep in all_deps:
            return framework
    return None


def run_type_check(project_dir: Path) -> CheckResult:
    """Run the best available type checker for this project."""
    framework = detect_framework(project_dir)

    if framework == "astro":
        if shutil.which("astro"):
            return run_check(
                "typecheck:astro", ["astro", "check"], cwd=str(project_dir)
            )
        return run_check(
            "typecheck:astro", ["npx", "astro", "check"], cwd=str(project_dir)
        )

    if framework == "next":
        if shutil.which("next"):
            return run_check("typecheck:next", ["next", "lint"], cwd=str(project_dir))
        return run_check(
            "typecheck:next", ["npx", "next", "lint"], cwd=str(project_dir)
        )

    # Default: tsc
    if shutil.which("tsc"):
        return run_check("typecheck:tsc", ["tsc", "--noEmit"], cwd=str(project_dir))
    return run_check("typecheck:tsc", ["npx", "tsc", "--noEmit"], cwd=str(project_dir))
