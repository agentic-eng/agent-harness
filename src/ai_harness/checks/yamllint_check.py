from pathlib import Path
import tempfile
from ai_harness.runner import run_check, CheckResult
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
