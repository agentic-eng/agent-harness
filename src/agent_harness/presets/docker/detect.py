"""Detect whether a project uses the Docker stack."""

from pathlib import Path

from agent_harness.git_files import find_files

DOCKER_INDICATORS = ["Dockerfile", "docker-compose.prod.yml", "docker-compose.yml"]


def detect_docker(project_dir: Path) -> bool:
    """Return True if the project contains Docker stack indicators."""
    return any((project_dir / f).is_file() for f in DOCKER_INDICATORS)


def find_dockerfiles(project_dir: Path) -> list[Path]:
    """Find all Dockerfiles in the project tree, as relative paths."""
    abs_paths = find_files(
        project_dir, ["**/Dockerfile", "Dockerfile", "**/Dockerfile.*", "Dockerfile.*"]
    )
    return sorted(p.relative_to(project_dir) for p in abs_paths)
