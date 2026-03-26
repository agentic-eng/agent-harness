import subprocess

from agent_harness.presets.universal.gitignore_tracked_fix import (
    fix_gitignore_tracked,
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


def test_fix_removes_tracked_ignored_files(tmp_path):
    """Fix should git rm --cached offending files."""
    _init_git(tmp_path)
    (tmp_path / "debug.log").write_text("log\n")
    subprocess.run(["git", "add", "debug.log"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add log"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    (tmp_path / ".gitignore").write_text("*.log\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add gitignore"],
        cwd=str(tmp_path),
        capture_output=True,
    )

    actions = fix_gitignore_tracked(tmp_path)
    assert len(actions) == 1
    assert "1 file" in actions[0]

    # Verify file is no longer tracked
    result = subprocess.run(
        ["git", "ls-files", "-ci", "--exclude-standard"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert result.stdout.strip() == ""
    # But file still exists on disk
    assert (tmp_path / "debug.log").exists()


def test_fix_nothing_to_do(tmp_path):
    """No tracked-but-ignored files -> empty actions."""
    _init_git(tmp_path)
    (tmp_path / ".gitignore").write_text("*.log\n")
    (tmp_path / "hello.py").write_text("print('hi')\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    actions = fix_gitignore_tracked(tmp_path)
    assert actions == []
