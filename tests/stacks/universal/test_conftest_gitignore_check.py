import subprocess

from agent_harness.stacks.universal.conftest_gitignore_check import run_conftest_gitignore


def _init_git(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)


def test_conftest_gitignore_no_file(tmp_path):
    """Skip gracefully when no .gitignore exists."""
    result = run_conftest_gitignore(tmp_path)
    assert result.passed


def test_gitignore_js_project_no_python_false_positives(tmp_path):
    """JS project should not be flagged for missing .venv or __pycache__."""
    _init_git(tmp_path)
    (tmp_path / ".gitignore").write_text(".env\nnode_modules/\ndist/\n")
    result = run_conftest_gitignore(tmp_path, stacks={"javascript"})
    assert result.passed, f"Should pass for JS project: {result.error or result.output}"


def test_gitignore_python_project_flags_venv(tmp_path):
    """Python project missing .venv should fail."""
    _init_git(tmp_path)
    (tmp_path / ".gitignore").write_text(".env\n")
    result = run_conftest_gitignore(tmp_path, stacks={"python"})
    assert not result.passed
    assert ".venv" in (result.error or result.output)
