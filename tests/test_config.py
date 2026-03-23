from pathlib import Path
from agent_harness.config import load_config


def test_load_config_from_file(tmp_path):
    (tmp_path / ".agent-harness.yml").write_text("stacks: [python, docker]\npython:\n  coverage_threshold: 90\n")
    config = load_config(tmp_path)
    assert "python" in config.stacks
    assert config.python.coverage_threshold == 90


def test_load_config_defaults(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    config = load_config(tmp_path)
    assert "python" in config.stacks
    assert config.python.coverage_threshold == 95


def test_load_config_with_exclude(tmp_path):
    (tmp_path / ".agent-harness.yml").write_text(
        "stacks: [python]\nexclude:\n  - _archive/\n  - vendor/\n"
    )
    config = load_config(tmp_path)
    assert "_archive/" in config.exclude
    assert "vendor/" in config.exclude


def test_load_config_exclude_defaults_empty(tmp_path):
    config = load_config(tmp_path)
    assert config.exclude == []


def test_load_config_disable_stack(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    (tmp_path / ".agent-harness.yml").write_text("stacks: [docker]\n")
    config = load_config(tmp_path)
    assert "python" not in config.stacks


def test_load_config_javascript(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}')
    (tmp_path / ".agent-harness.yml").write_text(
        "stacks: [javascript]\njavascript:\n  coverage_threshold: 90\n"
    )
    config = load_config(tmp_path)
    assert "javascript" in config.stacks
    assert config.javascript.coverage_threshold == 90


def test_load_config_javascript_defaults(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}')
    config = load_config(tmp_path)
    assert "javascript" in config.stacks
    assert config.javascript.coverage_threshold == 80
