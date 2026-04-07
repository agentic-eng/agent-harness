from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from agent_harness.config import load_config
from agent_harness.exclusions import get_excluded_patterns
from agent_harness.registry import PRESETS, UNIVERSAL
from agent_harness.runner import CheckResult
from agent_harness.workspace import discover_roots


def _is_skipped(check_name: str, skip_patterns: list[str]) -> bool:
    """Check if a check should be skipped.

    Supports exact match ("typecheck") and prefix match ("typecheck:tsc").
    A skip pattern "typecheck" skips all checks starting with "typecheck".
    """
    for pattern in skip_patterns:
        if check_name == pattern or check_name.startswith(pattern + ":"):
            return True
    return False


def run_lint(project_dir: Path) -> list[CheckResult]:
    config = load_config(project_dir)
    exclude = get_excluded_patterns(config.get("exclude", []))
    skip = config.get("skip", [])
    results = UNIVERSAL.run_checks(project_dir, config, exclude)
    for preset in PRESETS:
        if preset.name in config.get("stacks", set()):
            results.extend(preset.run_checks(project_dir, config, exclude))
    if skip:
        filtered = []
        for r in results:
            if _is_skipped(r.name, skip):
                filtered.append(
                    CheckResult(
                        name=r.name,
                        passed=True,
                        output="Skipped via .agent-harness.yml skip config",
                        duration_ms=0,
                    )
                )
            else:
                filtered.append(r)
        results = filtered
    return results


def run_lint_all(project_dir: Path) -> dict[Path, list[CheckResult]]:
    """Discover all subprojects and run lint in each. Returns {path: results}."""
    roots = discover_roots(project_dir)
    if not roots:
        return {project_dir: run_lint(project_dir)}

    results: dict[Path, list[CheckResult]] = {}
    with ThreadPoolExecutor() as pool:
        futures = {pool.submit(run_lint, root): root for root in roots}
        for future in as_completed(futures):
            root = futures[future]
            try:
                results[root] = future.result()
            except Exception as e:
                results[root] = [CheckResult(name="error", passed=False, error=str(e))]
    return results
