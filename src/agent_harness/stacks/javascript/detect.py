"""Detect whether a project uses the JavaScript/TypeScript stack."""

from pathlib import Path

JS_INDICATORS = ["package.json", "tsconfig.json", "deno.json"]


def detect_javascript(project_dir: Path) -> bool:
    """Return True if the project contains JavaScript/TypeScript stack indicators."""
    return any((project_dir / f).exists() for f in JS_INDICATORS)
