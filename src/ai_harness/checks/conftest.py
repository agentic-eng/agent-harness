"""Conftest-based checks using bundled Rego policies."""
from __future__ import annotations

import subprocess
from pathlib import Path

from ai_harness.runner import CheckResult, run_check

# Resolve bundled policies relative to this source file.
# Works when running via `uv run --project`.
POLICIES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "policies"


def _run_conftest(
    name: str,
    project_dir: Path,
    target_file: str,
    policy_subdir: str,
) -> CheckResult:
    """Run conftest test on a target file with policies from a subdirectory."""
    target = project_dir / target_file
    if not target.exists():
        return CheckResult(
            name=name,
            passed=True,
            output=f"Skipping {name}: {target_file} not found",
        )
    policy_path = POLICIES_DIR / policy_subdir
    cmd = [
        "conftest",
        "test",
        str(target),
        "--policy",
        str(policy_path),
        "--no-color",
        "--all-namespaces",
    ]
    return run_check(name, cmd, cwd=str(project_dir))


def run_conftest_dockerfile(project_dir: Path) -> CheckResult:
    """Run conftest on Dockerfile with bundled dockerfile policies."""
    return _run_conftest(
        "conftest-dockerfile",
        project_dir,
        "Dockerfile",
        "dockerfile",
    )


def run_conftest_compose(
    project_dir: Path, own_image_prefix: str = ""
) -> CheckResult:
    """Run conftest on docker-compose.prod.yml with bundled compose policies."""
    return _run_conftest(
        "conftest-compose",
        project_dir,
        "docker-compose.prod.yml",
        "compose",
    )


def run_conftest_python(project_dir: Path) -> CheckResult:
    """Run conftest on pyproject.toml with bundled python policies."""
    return _run_conftest(
        "conftest-python",
        project_dir,
        "pyproject.toml",
        "python",
    )


def run_conftest_gitignore(project_dir: Path) -> CheckResult:
    """Run conftest on .gitignore with bundled gitignore policies."""
    return _run_conftest(
        "conftest-gitignore",
        project_dir,
        ".gitignore",
        "gitignore",
    )


def run_conftest_json(project_dir: Path) -> CheckResult:
    """Validate JSON files via conftest parse --parser json."""
    name = "conftest-json"
    try:
        result = subprocess.run(
            ["git", "ls-files", "*.json", "**/*.json"],
            capture_output=True,
            text=True,
            cwd=str(project_dir),
            timeout=10,
        )
        json_files = [f for f in result.stdout.strip().splitlines() if f]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        json_files = []

    if not json_files:
        return CheckResult(
            name=name,
            passed=True,
            output="Skipping conftest-json: no JSON files found",
        )

    errors: list[str] = []
    for jf in json_files:
        cmd = ["conftest", "parse", "--parser", "json", str(project_dir / jf)]
        cr = run_check(f"{name}:{jf}", cmd, cwd=str(project_dir))
        if not cr.passed:
            errors.append(f"{jf}: {cr.error or cr.output}")

    if errors:
        return CheckResult(
            name=name,
            passed=False,
            error="\n".join(errors),
        )
    return CheckResult(
        name=name,
        passed=True,
        output=f"All {len(json_files)} JSON file(s) valid",
    )
