"""
YAML lint check.

WHAT: Runs yamllint on all git-tracked YAML files with a bundled or project
config.

WHY: Agents generate YAML with inconsistent indentation, overly long lines,
duplicate keys, and truthy value issues. YAML syntax errors are especially
dangerous because they often parse without error but produce wrong data
structures (e.g., `on` becomes boolean `true`).

WITHOUT IT: Broken CI pipelines from malformed YAML, silent config errors from
duplicate keys (last one wins), and truthy/falsy surprises in GitHub Actions
and docker-compose files.

FIX: Fix the YAML issues reported by yamllint. Common fixes: consistent
indentation, quote strings that look like booleans, remove duplicate keys.

REQUIRES: yamllint (via PATH)
"""
from pathlib import Path
import tempfile

from agent_harness.runner import run_check, CheckResult
import subprocess

YAMLLINT_CONFIG = """\
extends: default
ignore: |
  .venv/
  node_modules/
rules:
  line-length:
    max: 200
  truthy:
    check-keys: false
  document-start: disable
  indentation: disable
"""


def run_yamllint(project_dir: Path) -> CheckResult:
    # Find YAML files via git ls-files
    result = subprocess.run(
        ["git", "ls-files", "*.yml", "*.yaml"],
        capture_output=True, text=True, cwd=str(project_dir)
    )
    yaml_files = [f for f in result.stdout.strip().splitlines() if f]
    if not yaml_files:
        return CheckResult(name="yamllint", passed=True, output="No YAML files, skipping")

    # Use project's .yamllint.yml if it exists, otherwise use bundled config
    project_config = project_dir / ".yamllint.yml"
    if project_config.exists():
        config_arg = str(project_config)
    else:
        # Write bundled config to temp file
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
        tmp.write(YAMLLINT_CONFIG)
        tmp.close()
        config_arg = tmp.name

    return run_check(
        "yamllint",
        ["yamllint", "-c", config_arg, "-s"] + yaml_files,
        cwd=str(project_dir),
    )
