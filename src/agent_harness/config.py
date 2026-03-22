from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml
from agent_harness.detect import detect_stacks


@dataclass
class PythonConfig:
    coverage_threshold: int = 95
    line_length: int = 140
    max_file_lines: int = 500


@dataclass
class DockerConfig:
    own_image_prefix: str = ""


@dataclass
class HarnessConfig:
    stacks: set[str] = field(default_factory=set)
    python: PythonConfig = field(default_factory=PythonConfig)
    docker: DockerConfig = field(default_factory=DockerConfig)


def load_config(project_dir: Path) -> HarnessConfig:
    config = HarnessConfig()
    cfg_path = project_dir / ".harness.yml"
    if cfg_path.exists():
        raw = yaml.safe_load(cfg_path.read_text()) or {}
        if "stacks" in raw:
            config.stacks = set(raw["stacks"])
        if "python" in raw:
            for k, v in raw["python"].items():
                if hasattr(config.python, k):
                    setattr(config.python, k, v)
        if "docker" in raw:
            for k, v in raw["docker"].items():
                if hasattr(config.docker, k):
                    setattr(config.docker, k, v)
    if not config.stacks:
        config.stacks = detect_stacks(project_dir)
    return config
