"""Auto-fix for tracked-but-ignored files — runs git rm --cached."""

from __future__ import annotations

import subprocess
from pathlib import Path


def fix_gitignore_tracked(project_dir: Path) -> list[str]:
    """Remove tracked files that match .gitignore from git index."""
    result = subprocess.run(
        ["git", "ls-files", "-ci", "--exclude-standard"],
        capture_output=True,
        text=True,
        cwd=str(project_dir),
    )
    if result.returncode != 0:
        return []

    files = [f for f in result.stdout.strip().splitlines() if f]
    if not files:
        return []

    subprocess.run(
        ["git", "rm", "--cached"] + files,
        capture_output=True,
        text=True,
        cwd=str(project_dir),
    )
    count = len(files)
    return [f"gitignore-tracked: removed {count} file{'s' if count != 1 else ''} from git tracking"]
