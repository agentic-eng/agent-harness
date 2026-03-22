# tests/test_init.py
from pathlib import Path
from agent_harness.init.scaffold import scaffold_project

def test_scaffold_creates_files(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    actions = scaffold_project(tmp_path)
    assert (tmp_path / ".harness.yml").exists()
    assert (tmp_path / ".yamllint.yml").exists()
    assert (tmp_path / ".pre-commit-config.yaml").exists()
    assert any("CREATE" in a for a in actions)

def test_scaffold_skips_existing(tmp_path):
    (tmp_path / ".harness.yml").write_text("stacks: [python]")
    actions = scaffold_project(tmp_path)
    assert any("SKIP" in a and ".harness.yml" in a for a in actions)
    # Shouldn't overwrite
    assert (tmp_path / ".harness.yml").read_text() == "stacks: [python]"
