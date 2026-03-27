import subprocess

from agent_harness.presets.universal.gitignore_tracked_check import (
    run_gitignore_tracked,
)


def test_clean_repo_passes(git_repo):
    """No tracked-but-ignored files -> pass."""
    (git_repo / ".gitignore").write_text("*.log\n")
    (git_repo / "hello.py").write_text("print('hi')\n")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(git_repo),
        capture_output=True,
    )
    result = run_gitignore_tracked(git_repo)
    assert result.passed


def test_tracked_ignored_file_fails(git_repo):
    """A tracked file matching .gitignore -> fail with file listed."""
    (git_repo / "debug.log").write_text("log\n")
    subprocess.run(["git", "add", "debug.log"], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add log"],
        cwd=str(git_repo),
        capture_output=True,
    )
    # Now add .gitignore that excludes it
    (git_repo / ".gitignore").write_text("*.log\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add gitignore"],
        cwd=str(git_repo),
        capture_output=True,
    )
    result = run_gitignore_tracked(git_repo)
    assert not result.passed
    assert "debug.log" in result.error


def test_no_gitignore_passes(git_repo):
    """No .gitignore at all -> pass (nothing is ignored)."""
    (git_repo / "hello.py").write_text("print('hi')\n")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(git_repo),
        capture_output=True,
    )
    result = run_gitignore_tracked(git_repo)
    assert result.passed


def test_not_a_git_repo_passes(tmp_path):
    """Not a git repo -> pass gracefully."""
    result = run_gitignore_tracked(tmp_path)
    assert result.passed


def test_monorepo_subproject_detects_tracked_ignored(git_repo):
    """Root .gitignore applies to subproject — tracked-ignored file caught."""
    # Subproject with a .log file — committed before .gitignore exists
    subproject = git_repo / "services" / "api"
    subproject.mkdir(parents=True)
    (subproject / "debug.log").write_text("log\n")
    (subproject / "app.py").write_text("print('hi')\n")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(git_repo),
        capture_output=True,
    )
    # Now add root .gitignore that excludes *.log
    (git_repo / ".gitignore").write_text("*.log\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add gitignore"],
        cwd=str(git_repo),
        capture_output=True,
    )
    # Run check from subproject dir — should detect the tracked-ignored file
    result = run_gitignore_tracked(subproject)
    assert not result.passed
    assert "debug.log" in result.error


def test_monorepo_subproject_clean(git_repo):
    """Root .gitignore applies — subproject with no violations passes."""
    (git_repo / ".gitignore").write_text("*.log\n")
    subproject = git_repo / "services" / "api"
    subproject.mkdir(parents=True)
    (subproject / "app.py").write_text("print('hi')\n")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(git_repo),
        capture_output=True,
    )
    result = run_gitignore_tracked(subproject)
    assert result.passed
