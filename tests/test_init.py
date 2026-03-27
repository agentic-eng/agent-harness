# tests/test_init.py
from agent_harness.init.scaffold import scaffold_all, scaffold_project


def test_scaffold_creates_files(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    actions = scaffold_project(tmp_path, apply=True)
    assert (tmp_path / ".agent-harness.yml").exists()
    assert (tmp_path / ".yamllint.yml").exists()
    assert (tmp_path / ".pre-commit-config.yaml").exists()
    assert any("CREATE" in a for a in actions)


def test_scaffold_skips_existing(tmp_path):
    (tmp_path / ".agent-harness.yml").write_text("stacks: [python]")
    actions = scaffold_project(tmp_path, apply=True)
    assert any("SKIP" in a and ".agent-harness.yml" in a for a in actions)
    assert (tmp_path / ".agent-harness.yml").read_text() == "stacks: [python]"


def test_scaffold_creates_makefile(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    scaffold_project(tmp_path, apply=True)
    assert (tmp_path / "Makefile").exists()
    content = (tmp_path / "Makefile").read_text()
    assert "agent-harness lint" in content
    assert "pytest" in content


def test_scaffold_makefile_js_test_command(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}')
    scaffold_project(tmp_path, apply=True)
    content = (tmp_path / "Makefile").read_text()
    assert "npm test" in content


def test_scaffold_skips_existing_makefile(tmp_path):
    (tmp_path / "Makefile").write_text("custom: echo hi")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    actions = scaffold_project(tmp_path, apply=True)
    assert "SKIP  Makefile" in " ".join(actions)
    assert (tmp_path / "Makefile").read_text() == "custom: echo hi"


def test_report_mode_returns_empty(tmp_path):
    """Without apply, returns empty list (report only)."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    actions = scaffold_project(tmp_path, apply=False)
    assert actions == []
    assert not (tmp_path / ".agent-harness.yml").exists()


def test_apply_fixes_pyproject(tmp_path):
    """With apply, fixes are applied to pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text("""\
[project]
name = "x"

[tool.pytest.ini_options]
addopts = "--strict-markers --cov"
""")
    actions = scaffold_project(tmp_path, apply=True)
    content = (tmp_path / "pyproject.toml").read_text()
    assert "--cov-fail-under=95" in content
    assert "-v" in content
    assert any("FIXED" in a for a in actions)


def test_scaffold_all_discovers_subprojects(tmp_path):
    """scaffold_all finds and inits all project roots in a tree."""
    # Root project
    (tmp_path / "pyproject.toml").write_text("[project]\nname='root'")
    # Subproject
    sub = tmp_path / "services" / "api"
    sub.mkdir(parents=True)
    (sub / "pyproject.toml").write_text("[project]\nname='api'")

    results = scaffold_all(tmp_path, apply=True)
    assert tmp_path in results
    assert sub in results
    assert (tmp_path / ".agent-harness.yml").exists()
    assert (sub / ".agent-harness.yml").exists()


def test_scaffold_all_skips_already_initialized(tmp_path):
    """scaffold_all skips subprojects that already have harness config."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='root'")
    (tmp_path / ".agent-harness.yml").write_text("stacks: [python]")

    sub = tmp_path / "svc"
    sub.mkdir()
    (sub / "pyproject.toml").write_text("[project]\nname='svc'")

    results = scaffold_all(tmp_path, apply=True)
    # Root should skip .agent-harness.yml, sub should create it
    assert any("SKIP" in a and ".agent-harness.yml" in a for a in results[tmp_path])
    assert any("CREATE" in a and ".agent-harness.yml" in a for a in results[sub])
