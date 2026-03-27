from pathlib import Path

from agent_harness.presets.python.security_setup import check_python_security_setup


def test_no_pyproject(tmp_path: Path):
    issues = check_python_security_setup(tmp_path)
    assert issues == []


def test_pip_audit_in_dev_deps(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("""\
[project]
name = "test"

[dependency-groups]
dev = ["pip-audit>=2.7", "pytest"]
""")
    issues = check_python_security_setup(tmp_path)
    assert issues == []


def test_pip_audit_missing(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("""\
[project]
name = "test"

[dependency-groups]
dev = ["pytest", "ruff"]
""")
    issues = check_python_security_setup(tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "recommendation"
    assert "pip-audit" in issues[0].message
