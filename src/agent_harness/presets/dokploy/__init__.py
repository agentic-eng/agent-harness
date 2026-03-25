from pathlib import Path

from agent_harness.preset import Preset, PresetInfo, ToolInfo
from agent_harness.runner import CheckResult


class DokployPreset(Preset):
    name = "dokploy"

    def detect(self, project_dir: Path) -> bool:
        from .detect import detect_dokploy

        return detect_dokploy(project_dir)

    def run_checks(
        self, project_dir: Path, config: dict, exclude: list[str]
    ) -> list[CheckResult]:
        from .conftest_dokploy_check import run_conftest_dokploy

        return [run_conftest_dokploy(project_dir)]

    def run_fix(self, project_dir: Path, config: dict) -> list[str]:
        return []

    def get_info(self) -> PresetInfo:
        return PresetInfo(
            name="dokploy",
            tools=[
                ToolInfo(
                    "conftest",
                    "traefik.enable, dokploy-network",
                    "conftest",
                    "brew install conftest",
                ),
            ],
        )
