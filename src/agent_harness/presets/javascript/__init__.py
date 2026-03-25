from pathlib import Path

from agent_harness.preset import Preset, PresetInfo, ToolInfo
from agent_harness.runner import CheckResult


class JavaScriptPreset(Preset):
    name = "javascript"

    def detect(self, project_dir: Path) -> bool:
        from .detect import detect_javascript

        return detect_javascript(project_dir)

    def run_checks(
        self, project_dir: Path, config: dict, exclude: list[str]
    ) -> list[CheckResult]:
        from .biome_check import run_biome
        from .conftest_package_check import run_conftest_package
        from .type_check import run_type_check

        results = []
        results.extend(run_biome(project_dir))
        results.append(run_type_check(project_dir))
        results.append(run_conftest_package(project_dir))
        return results

    def run_fix(self, project_dir: Path, config: dict) -> list[str]:
        from .fix import run_javascript_fix

        return run_javascript_fix(project_dir)

    def get_info(self) -> PresetInfo:
        return PresetInfo(
            name="javascript",
            tools=[
                ToolInfo(
                    "biome",
                    "linting + formatting",
                    "biome",
                    "npm install --save-dev @biomejs/biome",
                ),
                ToolInfo(
                    "type checker",
                    "astro check / next lint / tsc",
                    "tsc",
                    "npm install --save-dev typescript",
                ),
                ToolInfo(
                    "conftest",
                    "package.json enforcement",
                    "conftest",
                    "brew install conftest",
                ),
            ],
        )
