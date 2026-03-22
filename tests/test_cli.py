from click.testing import CliRunner
from ai_harness.cli import cli


def test_lint_empty_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["lint"])
    assert "passed" in result.output
