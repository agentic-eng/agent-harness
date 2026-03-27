import subprocess

from agent_harness.presets.universal.gitignore_tracked_fix import (
    fix_gitignore_tracked,
)


def test_fix_removes_tracked_ignored_files(git_repo):
    """Fix should git rm --cached offending files."""
    (git_repo / "debug.log").write_text("log\n")
    subprocess.run(["git", "add", "debug.log"], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add log"],
        cwd=str(git_repo),
        capture_output=True,
    )
    (git_repo / ".gitignore").write_text("*.log\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add gitignore"],
        cwd=str(git_repo),
        capture_output=True,
    )

    actions = fix_gitignore_tracked(git_repo)
    assert len(actions) == 1
    assert "1 file" in actions[0]

    # Verify file is no longer tracked
    result = subprocess.run(
        ["git", "ls-files", "-ci", "--exclude-standard"],
        capture_output=True,
        text=True,
        cwd=str(git_repo),
    )
    assert result.stdout.strip() == ""
    # But file still exists on disk
    assert (git_repo / "debug.log").exists()


def test_fix_nothing_to_do(git_repo):
    """No tracked-but-ignored files -> empty actions."""
    (git_repo / ".gitignore").write_text("*.log\n")
    (git_repo / "hello.py").write_text("print('hi')\n")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(git_repo),
        capture_output=True,
    )
    actions = fix_gitignore_tracked(git_repo)
    assert actions == []
