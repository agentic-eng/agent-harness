from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from agent_harness.config import load_config
from agent_harness.exclusions import get_excluded_patterns
from agent_harness.runner import CheckResult
from agent_harness.stacks.universal.yamllint_check import run_yamllint
from agent_harness.stacks.universal.conftest_json_check import run_conftest_json
from agent_harness.stacks.universal.conftest_gitignore_check import (
    run_conftest_gitignore,
)
from agent_harness.stacks.python.ruff_check import run_ruff
from agent_harness.stacks.python.ty_check import run_ty
from agent_harness.stacks.python.conftest_python_check import run_conftest_python
from agent_harness.stacks.universal.file_length_check import run_file_length
from agent_harness.stacks.docker.hadolint_check import run_hadolint
from agent_harness.stacks.docker.conftest_dockerfile_check import (
    run_conftest_dockerfile,
)
from agent_harness.stacks.docker.conftest_compose_check import run_conftest_compose
from agent_harness.stacks.dokploy.conftest_dokploy_check import run_conftest_dokploy
from agent_harness.stacks.javascript.biome_check import run_biome
from agent_harness.stacks.javascript.type_check import run_type_check
from agent_harness.stacks.javascript.conftest_package_check import run_conftest_package


def run_lint(project_dir: Path) -> list[CheckResult]:
    config = load_config(project_dir)
    exclude = get_excluded_patterns(config.exclude)
    results: list[CheckResult] = []

    # Universal checks
    results.append(run_conftest_gitignore(project_dir, stacks=config.stacks))
    results.append(run_conftest_json(project_dir, exclude_patterns=exclude))
    results.append(run_yamllint(project_dir, exclude_patterns=exclude))
    # Pass Python max_file_lines override if configured
    file_length_override = {}
    if "python" in config.stacks and config.python.max_file_lines != 500:
        file_length_override[".py"] = config.python.max_file_lines
    results.append(
        run_file_length(
            project_dir,
            max_lines_override=file_length_override or None,
            exclude_patterns=exclude,
        )
    )

    # Python checks
    if "python" in config.stacks:
        results.extend(run_ruff(project_dir))  # returns list
        results.append(run_ty(project_dir))
        results.append(run_conftest_python(project_dir))

    # Docker checks
    if "docker" in config.stacks:
        results.append(run_conftest_dockerfile(project_dir))
        results.append(
            run_conftest_compose(project_dir, config.docker.own_image_prefix)
        )
        results.append(run_hadolint(project_dir))

    # Dokploy checks
    if "dokploy" in config.stacks:
        results.append(run_conftest_dokploy(project_dir))

    # JavaScript checks
    if "javascript" in config.stacks:
        results.extend(run_biome(project_dir))
        results.append(run_type_check(project_dir))
        results.append(run_conftest_package(project_dir))

    return results


def run_lint_all(project_dir: Path) -> dict[Path, list[CheckResult]]:
    """Discover all subprojects and run lint in each. Returns {path: results}."""
    from agent_harness.workspace import discover_roots

    roots = discover_roots(project_dir)
    if not roots:
        # No .agent-harness.yml found anywhere — just run in current dir
        return {project_dir: run_lint(project_dir)}

    all_results: dict[Path, list[CheckResult]] = {}
    with ThreadPoolExecutor() as pool:
        futures = {pool.submit(run_lint, root): root for root in roots}
        for future in as_completed(futures):
            root = futures[future]
            try:
                all_results[root] = future.result()
            except Exception as e:
                all_results[root] = [
                    CheckResult(name="error", passed=False, error=str(e))
                ]
    return all_results
