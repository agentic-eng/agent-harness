from pathlib import Path
from agent_harness.config import load_config
from agent_harness.exclusions import get_excluded_patterns
from agent_harness.runner import CheckResult
from agent_harness.stacks.universal.yamllint_check import run_yamllint
from agent_harness.stacks.universal.conftest_json_check import run_conftest_json
from agent_harness.stacks.universal.conftest_gitignore_check import run_conftest_gitignore
from agent_harness.stacks.python.ruff_check import run_ruff
from agent_harness.stacks.python.ty_check import run_ty
from agent_harness.stacks.python.conftest_python_check import run_conftest_python
from agent_harness.stacks.python.file_length_check import run_file_length
from agent_harness.stacks.docker.hadolint_check import run_hadolint
from agent_harness.stacks.docker.conftest_dockerfile_check import run_conftest_dockerfile
from agent_harness.stacks.docker.conftest_compose_check import run_conftest_compose


def run_lint(project_dir: Path) -> list[CheckResult]:
    config = load_config(project_dir)
    exclude = get_excluded_patterns(config.exclude)
    results: list[CheckResult] = []

    # Universal checks
    results.append(run_conftest_gitignore(project_dir))
    results.append(run_conftest_json(project_dir, exclude_patterns=exclude))
    results.append(run_yamllint(project_dir, exclude_patterns=exclude))

    # Python checks
    if "python" in config.stacks:
        results.extend(run_ruff(project_dir))  # returns list
        results.append(run_ty(project_dir))
        results.append(run_conftest_python(project_dir))
        results.append(run_file_length(project_dir, config.python.max_file_lines))

    # Docker checks
    if "docker" in config.stacks:
        results.append(run_conftest_dockerfile(project_dir))
        results.append(run_conftest_compose(project_dir, config.docker.own_image_prefix))
        results.append(run_hadolint(project_dir))

    return results
