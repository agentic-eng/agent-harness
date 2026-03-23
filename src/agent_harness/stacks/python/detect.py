"""Detect whether a project uses the Python stack."""

from pathlib import Path

PYTHON_INDICATORS = ["pyproject.toml", "setup.py", "requirements.txt", "uv.lock"]


def detect_python(project_dir: Path) -> bool:
    """Return True if the project contains Python stack indicators."""
    return any((project_dir / f).exists() for f in PYTHON_INDICATORS)
