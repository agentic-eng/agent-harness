"""Detect whether a project deploys to Dokploy."""

from pathlib import Path

COMPOSE_FILES = ["docker-compose.prod.yml", "docker-compose.yml"]


def detect_dokploy(project_dir: Path) -> bool:
    """Return True if any compose file references dokploy-network."""
    for f in COMPOSE_FILES:
        path = project_dir / f
        if path.exists():
            content = path.read_text()
            if "dokploy-network" in content:
                return True
    return False
