import subprocess

from agent_harness.presets.universal.gitignore_tracked_check import (
    run_gitignore_tracked,
)


def _init_git(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path),
        capture_output=True,
    )


def test_clean_repo_passes(tmp_path):
    """No tracked-but-ignored files -> pass."""
    _init_git(tmp_path)
    (tmp_path / ".gitignore").write_text("*.log\n")
    (tmp_path / "hello.py").write_text("print('hi')\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    result = run_gitignore_tracked(tmp_path)
    assert result.passed


def test_tracked_ignored_file_fails(tmp_path):
    """A tracked file matching .gitignore -> fail with file listed."""
    _init_git(tmp_path)
    (tmp_path / "debug.log").write_text("log\n")
    subprocess.run(["git", "add", "debug.log"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add log"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    # Now add .gitignore that excludes it
    (tmp_path / ".gitignore").write_text("*.log\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add gitignore"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    result = run_gitignore_tracked(tmp_path)
    assert not result.passed
    assert "debug.log" in result.error


def test_no_gitignore_passes(tmp_path):
    """No .gitignore at all -> pass (nothing is ignored)."""
    _init_git(tmp_path)
    (tmp_path / "hello.py").write_text("print('hi')\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    result = run_gitignore_tracked(tmp_path)
    assert result.passed


def test_not_a_git_repo_passes(tmp_path):
    """Not a git repo -> pass gracefully."""
    result = run_gitignore_tracked(tmp_path)
    assert result.passed
