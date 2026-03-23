"""Stack detection orchestrator — delegates to per-stack detect modules."""

from pathlib import Path

from agent_harness.stacks.python.detect import detect_python
from agent_harness.stacks.docker.detect import detect_docker
from agent_harness.stacks.javascript.detect import detect_javascript
from agent_harness.stacks.dokploy.detect import detect_dokploy


def detect_stacks(project_dir: Path) -> set[str]:
    """Detect which stacks a project uses based on file presence."""
    stacks = set()
    if detect_python(project_dir):
        stacks.add("python")
    if detect_docker(project_dir):
        stacks.add("docker")
    if detect_javascript(project_dir):
        stacks.add("javascript")
    if detect_dokploy(project_dir):
        stacks.add("dokploy")
    return stacks
