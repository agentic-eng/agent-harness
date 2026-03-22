"""Stack detection orchestrator — delegates to per-stack detect modules."""
from pathlib import Path

from agent_harness.stacks.python.detect import detect_python
from agent_harness.stacks.docker.detect import detect_docker


def detect_stacks(project_dir: Path) -> set[str]:
    """Detect which stacks a project uses based on file presence."""
    stacks = set()
    if detect_python(project_dir):
        stacks.add("python")
    if detect_docker(project_dir):
        stacks.add("docker")
    return stacks
