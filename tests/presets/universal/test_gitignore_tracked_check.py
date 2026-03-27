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


def test_monorepo_subproject_detects_tracked_ignored(tmp_path):
    """Root .gitignore applies to subproject — tracked-ignored file caught."""
    _init_git(tmp_path)
    # Subproject with a .log file — committed before .gitignore exists
    subproject = tmp_path / "services" / "api"
    subproject.mkdir(parents=True)
    (subproject / "debug.log").write_text("log\n")
    (subproject / "app.py").write_text("print('hi')\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    # Now add root .gitignore that excludes *.log
    (tmp_path / ".gitignore").write_text("*.log\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add gitignore"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    # Run check from subproject dir — should detect the tracked-ignored file
    result = run_gitignore_tracked(subproject)
    assert not result.passed
    assert "debug.log" in result.error


def test_monorepo_subproject_clean(tmp_path):
    """Root .gitignore applies — subproject with no violations passes."""
    _init_git(tmp_path)
    (tmp_path / ".gitignore").write_text("*.log\n")
    subproject = tmp_path / "services" / "api"
    subproject.mkdir(parents=True)
    (subproject / "app.py").write_text("print('hi')\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    result = run_gitignore_tracked(subproject)
    assert result.passed
