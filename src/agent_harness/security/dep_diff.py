"""Dependency diff detection — find newly added packages vs a base branch."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import tomllib


def parse_python_deps(content: str) -> set[str]:
    """Extract dependency names from pyproject.toml content."""
    data = tomllib.loads(content)
    deps: set[str] = set()

    for dep in data.get("project", {}).get("dependencies", []):
        name = _extract_python_dep_name(dep)
        if name:
            deps.add(name)

    for group_deps in data.get("project", {}).get("optional-dependencies", {}).values():
        for dep in group_deps:
            name = _extract_python_dep_name(dep)
            if name:
                deps.add(name)

    for group_deps in data.get("dependency-groups", {}).values():
        for dep in group_deps:
            if isinstance(dep, str):
                name = _extract_python_dep_name(dep)
                if name:
                    deps.add(name)

    return deps


def _extract_python_dep_name(specifier: str) -> str | None:
    """Extract normalized package name from a PEP 508 dependency specifier."""
    match = re.match(r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)", specifier)
    if not match:
        return None
    return match.group(1).lower().replace("_", "-")


def parse_js_deps(content: str) -> set[str]:
    """Extract dependency names from package.json content."""
    data = json.loads(content)
    deps: set[str] = set()
    for key in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        deps.update(data.get(key, {}).keys())
    return deps


def _get_base_file(base_branch: str, file_path: str, project_dir: Path) -> str | None:
    """Get file content from base branch via git show."""
    result = subprocess.run(
        ["git", "show", f"{base_branch}:{file_path}"],
        capture_output=True,
        text=True,
        cwd=str(project_dir),
    )
    if result.returncode != 0:
        return None
    return result.stdout


def detect_new_deps(project_dir: Path, base_branch: str = "origin/main") -> set[str]:
    """Detect newly added dependencies compared to a base branch.

    Returns set of package names that are in the current working tree
    but not in the base branch. If the base branch doesn't exist or
    the manifest file is new, all current deps are considered new.
    """
    current_deps: set[str] = set()
    base_deps: set[str] = set()

    # Python
    pyproject_path = project_dir / "pyproject.toml"
    if pyproject_path.exists():
        current_deps |= parse_python_deps(pyproject_path.read_text())
        base_content = _get_base_file(base_branch, "pyproject.toml", project_dir)
        if base_content is not None:
            base_deps |= parse_python_deps(base_content)

    # JavaScript
    pkg_json_path = project_dir / "package.json"
    if pkg_json_path.exists():
        current_deps |= parse_js_deps(pkg_json_path.read_text())
        base_content = _get_base_file(base_branch, "package.json", project_dir)
        if base_content is not None:
            base_deps |= parse_js_deps(base_content)

    return current_deps - base_deps
