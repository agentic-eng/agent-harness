# tests/test_lint_all.py
import subprocess
from agent_harness.lint import run_lint_all


def _init_git(path):
    subprocess.run(["git", "init"], cwd=str(path), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(path), capture_output=True)


def test_lint_all_single_root(tmp_path):
    """Single project with .agent-harness.yml returns results for that root."""
    (tmp_path / ".agent-harness.yml").write_text("stacks: []\n")
    _init_git(tmp_path)
    results = run_lint_all(tmp_path)
    assert tmp_path in results


def test_lint_all_multiple_roots(tmp_path):
    """Multiple subprojects each get their own results."""
    (tmp_path / ".agent-harness.yml").write_text("stacks: []\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / ".agent-harness.yml").write_text("stacks: []\n")
    _init_git(tmp_path)
    results = run_lint_all(tmp_path)
    assert tmp_path in results
    assert sub in results


def test_lint_all_no_dotfiles_runs_cwd(tmp_path):
    """If no .agent-harness.yml found, fall back to running in cwd."""
    _init_git(tmp_path)
    results = run_lint_all(tmp_path)
    assert tmp_path in results
