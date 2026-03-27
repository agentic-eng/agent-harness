from click.testing import CliRunner
from agent_harness.cli import cli


def test_lint_empty_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["lint"])
    assert "passed" in result.output


def test_fix_empty_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["fix"])
    assert "Fixing" in result.output
    assert "Linting" in result.output


def test_audit_command_removed():
    runner = CliRunner()
    result = runner.invoke(cli, ["audit"])
    assert result.exit_code != 0
    assert "No such command" in result.output or "Usage" in result.output


def test_security_audit_command_exists():
    """security-audit command is registered."""
    runner = CliRunner()
    result = runner.invoke(cli, ["security-audit", "--help"])
    assert result.exit_code == 0
    assert "security" in result.output.lower()
