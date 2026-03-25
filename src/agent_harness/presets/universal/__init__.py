from pathlib import Path

from agent_harness.preset import Preset, PresetInfo, ToolInfo
from agent_harness.runner import CheckResult


class UniversalPreset(Preset):
    name = "universal"

    def detect(self, project_dir: Path) -> bool:
        return True  # Always applies

    def run_checks(
        self, project_dir: Path, config: dict, exclude: list[str]
    ) -> list[CheckResult]:
        from .conftest_gitignore_check import run_conftest_gitignore
        from .conftest_json_check import run_conftest_json
        from .file_length_check import run_file_length
        from .yamllint_check import run_yamllint

        results = []
        results.append(
            run_conftest_gitignore(project_dir, stacks=config.get("stacks", set()))
        )
        results.append(run_conftest_json(project_dir, exclude_patterns=exclude))
        results.append(run_yamllint(project_dir, exclude_patterns=exclude))

        # Pass Python max_file_lines override if configured
        file_length_override = {}
        python_config = config.get("python", {})
        if isinstance(python_config, dict) and "python" in config.get("stacks", set()):
            max_file_lines = python_config.get("max_file_lines", 500)
            if max_file_lines != 500:
                file_length_override[".py"] = max_file_lines
        results.append(
            run_file_length(
                project_dir,
                max_lines_override=file_length_override or None,
                exclude_patterns=exclude,
            )
        )
        return results

    def run_fix(self, project_dir: Path, config: dict) -> list[str]:
        return []

    def get_info(self) -> PresetInfo:
        return PresetInfo(
            name="universal",
            tools=[
                ToolInfo(
                    "yamllint", "YAML validation", "yamllint", "pip install yamllint"
                ),
                ToolInfo(
                    "conftest",
                    "gitignore and JSON validation",
                    "conftest",
                    "brew install conftest",
                ),
            ],
        )
