"""Stack detection orchestrator — delegates to per-stack detect modules."""

from pathlib import Path

from agent_harness.stacks.python.detect import detect_python
from agent_harness.stacks.docker.detect import detect_docker
from agent_harness.stacks.javascript.detect import detect_javascript
from agent_harness.stacks.dokploy.detect import detect_dokploy


from agent_harness.workspace import SKIP_DIRS


def detect_all(project_dir: Path, max_depth: int = 4) -> dict[Path, set[str]]:
    """Detect stacks in root and subdirectories. Returns {path: stacks}."""
    results: dict[Path, set[str]] = {}
    _detect_recursive(project_dir, project_dir, results, depth=0, max_depth=max_depth)
    return results


def _detect_recursive(
    root: Path, directory: Path, results: dict, depth: int, max_depth: int
) -> None:
    if depth > max_depth:
        return
    stacks = detect_stacks(directory)
    if stacks:
        results[directory] = stacks
    try:
        children = sorted(directory.iterdir())
    except PermissionError:
        return
    for child in children:
        if child.is_dir() and child.name not in SKIP_DIRS and not child.name.startswith("."):
            _detect_recursive(root, child, results, depth + 1, max_depth)


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
