"""Detect whether a project uses the Docker stack."""

from pathlib import Path

DOCKER_INDICATORS = ["Dockerfile", "docker-compose.prod.yml", "docker-compose.yml"]


def detect_docker(project_dir: Path) -> bool:
    """Return True if the project contains Docker stack indicators."""
    return any((project_dir / f).exists() for f in DOCKER_INDICATORS)
