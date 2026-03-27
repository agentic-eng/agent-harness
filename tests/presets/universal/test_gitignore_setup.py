from agent_harness.presets.universal.gitignore_setup import check_gitignore_setup


def test_missing_patterns_flagged(tmp_path):
    """Gitignore missing OS patterns -> critical issue reported."""
    (tmp_path / ".gitignore").write_text(".env\n__pycache__/\n")
    issues = check_gitignore_setup(tmp_path, stacks={"python"})
    assert len(issues) > 0
    assert any(i.severity == "critical" for i in issues)
    # Should mention .DS_Store (from macOS template)
    messages = " ".join(i.message for i in issues)
    assert ".DS_Store" in messages


def test_complete_gitignore_passes(tmp_path):
    """Gitignore with all expected patterns -> no issues."""
    # Load actual templates to build a complete .gitignore
    from agent_harness.presets.universal.gitignore_setup import _load_expected_patterns

    patterns = _load_expected_patterns({"python"})
    (tmp_path / ".gitignore").write_text("\n".join(patterns) + "\n")
    issues = check_gitignore_setup(tmp_path, stacks={"python"})
    assert issues == []


def test_no_gitignore_flagged(tmp_path):
    """No .gitignore at all -> critical issue."""
    issues = check_gitignore_setup(tmp_path, stacks=set())
    assert len(issues) == 1
    assert issues[0].severity == "critical"
    assert issues[0].fixable


def test_fix_appends_missing_patterns(tmp_path):
    """Fix should append missing patterns without removing existing ones."""
    (tmp_path / ".gitignore").write_text("# My custom rules\n.env\n")
    issues = check_gitignore_setup(tmp_path, stacks={"python"})
    fixable = [i for i in issues if i.fixable]
    assert len(fixable) > 0

    # Apply the fix
    for issue in fixable:
        assert issue.fix is not None
        issue.fix(tmp_path)

    content = (tmp_path / ".gitignore").read_text()
    # Original content preserved
    assert "# My custom rules" in content
    assert ".env" in content
    # New patterns appended
    assert ".DS_Store" in content
    assert "# Added by agent-harness" in content


def test_fix_creates_gitignore_if_missing(tmp_path):
    """Fix should create .gitignore from templates if none exists."""
    issues = check_gitignore_setup(tmp_path, stacks={"python"})
    fixable = [i for i in issues if i.fixable]
    assert len(fixable) == 1

    assert fixable[0].fix is not None
    fixable[0].fix(tmp_path)

    content = (tmp_path / ".gitignore").read_text()
    assert ".DS_Store" in content
    assert "__pycache__" in content


def test_monorepo_subproject_no_gitignore(tmp_path):
    """Subproject without own .gitignore -> flagged as missing.

    In a monorepo, the root .gitignore covers subprojects. But the setup
    check runs per-subproject and looks for a local .gitignore. This test
    documents the current behavior: subprojects without their own .gitignore
    are flagged.
    """
    # Root has .gitignore
    (tmp_path / ".gitignore").write_text(".DS_Store\n__pycache__/\n")
    # Subproject has no .gitignore
    subproject = tmp_path / "services" / "api"
    subproject.mkdir(parents=True)
    (subproject / "pyproject.toml").write_text("[project]\nname='api'\n")

    issues = check_gitignore_setup(subproject, stacks={"python"})
    # Currently flags as missing — documents known monorepo limitation
    assert len(issues) == 1
    assert "No .gitignore found" in issues[0].message
