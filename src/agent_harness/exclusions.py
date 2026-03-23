"""
File exclusion system.

WHAT: Provides default and configurable file exclusion patterns for all checks.

WHY: Without exclusions, agent-harness scans lock files, build output, archives,
and vendored code. This wastes time (yamllint on pnpm-lock.yaml: 1.7s) and
produces false positives (JSONC parse failures on tsconfig.json in _archive/).

WITHOUT IT: 2.5s lint runs that should be 200ms, false positives on generated
files, agents fixing issues in files they shouldn't touch.

FIX: Add patterns to `exclude:` in .agent-harness.yml.
"""
from __future__ import annotations

import fnmatch

DEFAULT_EXCLUSIONS = [
    # Lock files
    "*.lock",
    "*-lock.*",
    "package-lock.json",
    # Build output
    "dist/",
    ".astro/",
    ".next/",
    ".nuxt/",
    # Dependencies
    "node_modules/",
    ".venv/",
    # Caches
    "__pycache__/",
    ".pytest_cache/",
    ".ruff_cache/",
    # Archives
    "_archive/",
]


def get_excluded_patterns(config_exclude: list[str]) -> list[str]:
    """Merge default exclusions with config-provided ones."""
    return DEFAULT_EXCLUSIONS + config_exclude


def is_excluded(filepath: str, patterns: list[str]) -> bool:
    """Check if a filepath matches any exclusion pattern."""
    for pattern in patterns:
        # Directory prefix match: "dist/" matches "dist/foo/bar.js"
        if pattern.endswith("/") and filepath.startswith(pattern):
            return True
        # Also match if any path segment matches directory pattern
        if pattern.endswith("/"):
            dir_name = pattern.rstrip("/")
            if f"/{dir_name}/" in f"/{filepath}" or filepath.startswith(f"{dir_name}/"):
                return True
        # Glob match: "*.lock" matches "poetry.lock"
        if fnmatch.fnmatch(filepath, pattern):
            return True
        # Also match basename: "*-lock.*" matches "path/to/pnpm-lock.yaml"
        if fnmatch.fnmatch(filepath.split("/")[-1], pattern):
            return True
    return False
