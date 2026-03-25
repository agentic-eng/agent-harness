from pathlib import Path

from agent_harness.preset import Preset, PresetInfo, ToolInfo
from agent_harness.runner import CheckResult


class PythonPreset(Preset):
    name = "python"

    def detect(self, project_dir: Path) -> bool:
        from .detect import detect_python

        return detect_python(project_dir)

    def run_checks(
        self, project_dir: Path, config: dict, exclude: list[str]
    ) -> list[CheckResult]:
        from .conftest_check import run_conftest_python
        from .ruff_check import run_ruff
        from .ty_check import run_ty

        results = []
        results.extend(run_ruff(project_dir))
        results.append(run_ty(project_dir))
        results.append(run_conftest_python(project_dir))
        return results

    def run_setup(self, project_dir, config):
        from .setup import check_python_setup

        return check_python_setup(project_dir)

    def run_fix(self, project_dir: Path, config: dict) -> list[str]:
        from .fix import run_python_fix

        return run_python_fix(project_dir)

    def get_info(self) -> PresetInfo:
        return PresetInfo(
            name="python",
            tools=[
                ToolInfo("ruff", "linting + formatting", "ruff", "uv add ruff --dev"),
                ToolInfo("ty", "type checking", "ty", "uv add ty --dev"),
                ToolInfo(
                    "conftest",
                    "pyproject.toml enforcement",
                    "conftest",
                    "brew install conftest",
                ),
            ],
        )
