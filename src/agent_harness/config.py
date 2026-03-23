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
class JavaScriptConfig:
    coverage_threshold: int = 80


@dataclass
class HarnessConfig:
    stacks: set[str] = field(default_factory=set)
    exclude: list[str] = field(default_factory=list)
    python: PythonConfig = field(default_factory=PythonConfig)
    docker: DockerConfig = field(default_factory=DockerConfig)
    javascript: JavaScriptConfig = field(default_factory=JavaScriptConfig)


def load_config(project_dir: Path) -> HarnessConfig:
    config = HarnessConfig()
    cfg_path = project_dir / ".agent-harness.yml"
    if cfg_path.exists():
        raw = yaml.safe_load(cfg_path.read_text()) or {}
        if "stacks" in raw:
            config.stacks = set(raw["stacks"])
        if "exclude" in raw:
            config.exclude = list(raw["exclude"])
        if "python" in raw:
            for k, v in raw["python"].items():
                if hasattr(config.python, k):
                    setattr(config.python, k, v)
        if "docker" in raw:
            for k, v in raw["docker"].items():
                if hasattr(config.docker, k):
                    setattr(config.docker, k, v)
        if "javascript" in raw:
            for k, v in raw["javascript"].items():
                if hasattr(config.javascript, k):
                    setattr(config.javascript, k, v)
    if not config.stacks:
        config.stacks = detect_stacks(project_dir)
    return config
