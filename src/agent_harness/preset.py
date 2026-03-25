"""Preset interface — every preset implements this."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agent_harness.runner import CheckResult
from agent_harness.setup import SetupIssue


@dataclass
class ToolInfo:
    name: str
    description: str
    binary: str
    install_hint: str


@dataclass
class PresetInfo:
    name: str
    tools: list[ToolInfo] = field(default_factory=list)


class Preset:
    """Base class for all presets."""

    name: str = ""

    def detect(self, project_dir: Path) -> bool:
        return False

    def run_checks(
        self, project_dir: Path, config: dict, exclude: list[str]
    ) -> list[CheckResult]:
        return []

    def run_fix(self, project_dir: Path, config: dict) -> list[str]:
        return []

    def run_setup(self, project_dir: Path, config: dict) -> list[SetupIssue]:
        """Run setup checks. Returns issues with optional fixes."""
        return []

    def get_info(self) -> PresetInfo:
        return PresetInfo(name=self.name)
