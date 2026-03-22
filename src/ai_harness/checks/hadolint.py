from pathlib import Path
from ai_harness.runner import run_check, CheckResult


def run_hadolint(project_dir: Path) -> CheckResult:
    dockerfile = project_dir / "Dockerfile"
    if not dockerfile.exists():
        return CheckResult(name="hadolint", passed=True, output="No Dockerfile, skipping")
    return run_check("hadolint", ["hadolint", str(dockerfile)], cwd=str(project_dir))
