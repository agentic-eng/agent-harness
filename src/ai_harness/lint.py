from pathlib import Path
from ai_harness.config import load_config
from ai_harness.runner import CheckResult
from ai_harness.checks.conftest import (
    run_conftest_dockerfile, run_conftest_compose,
    run_conftest_python, run_conftest_gitignore, run_conftest_json,
)
from ai_harness.checks.hadolint import run_hadolint
from ai_harness.checks.yamllint_check import run_yamllint
from ai_harness.checks.ruff import run_ruff
from ai_harness.checks.file_length import run_file_length


def run_lint(project_dir: Path) -> list[CheckResult]:
    config = load_config(project_dir)
    results: list[CheckResult] = []

    # Universal checks
    results.append(run_conftest_gitignore(project_dir))
    results.append(run_conftest_json(project_dir))
    results.append(run_yamllint(project_dir))

    # Python checks
    if "python" in config.stacks:
        results.extend(run_ruff(project_dir))  # returns list
        results.append(run_conftest_python(project_dir))
        results.append(run_file_length(project_dir, config.python.max_file_lines))

    # Docker checks
    if "docker" in config.stacks:
        results.append(run_conftest_dockerfile(project_dir))
        results.append(run_conftest_compose(project_dir, config.docker.own_image_prefix))
        results.append(run_hadolint(project_dir))

    return results
