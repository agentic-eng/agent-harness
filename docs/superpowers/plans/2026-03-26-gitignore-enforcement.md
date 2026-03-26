# Gitignore Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect tracked-but-ignored files in lint and ensure .gitignore completeness during init, using vendored github/gitignore templates.

**Architecture:** Two features in the universal preset. Lint runs `git ls-files -ci --exclude-standard` every time (milliseconds). Init loads vendored templates per detected stack, compares against existing .gitignore patterns, and appends missing ones. Templates are vendored from github/gitignore with a manual refresh script.

**Tech Stack:** Python, git, subprocess

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `src/agent_harness/presets/universal/gitignore_tracked_check.py` | Lint check: detect tracked files matching .gitignore |
| Create | `tests/presets/universal/test_gitignore_tracked_check.py` | Tests for tracked-file check |
| Create | `src/agent_harness/presets/universal/gitignore_setup.py` | Init check: gitignore completeness against templates |
| Create | `tests/presets/universal/test_gitignore_setup.py` | Tests for completeness check |
| Create | `src/agent_harness/templates/gitignore/Python.gitignore` | Vendored template |
| Create | `src/agent_harness/templates/gitignore/Node.gitignore` | Vendored template |
| Create | `src/agent_harness/templates/gitignore/macOS.gitignore` | Vendored OS global |
| Create | `src/agent_harness/templates/gitignore/Windows.gitignore` | Vendored OS global |
| Create | `src/agent_harness/templates/gitignore/Linux.gitignore` | Vendored OS global |
| Create | `src/agent_harness/templates/gitignore/SOURCE.md` | Attribution to github/gitignore |
| Create | `scripts/update-gitignore-templates.sh` | Manual refresh from GitHub API |
| Modify | `src/agent_harness/presets/universal/__init__.py` | Wire in new check + setup + fix |

---

### Task 1: Lint check — tracked-but-ignored file detection

**Files:**
- Create: `src/agent_harness/presets/universal/gitignore_tracked_check.py`
- Create: `tests/presets/universal/test_gitignore_tracked_check.py`

- [ ] **Step 1: Write the failing test for clean repo (no violations)**

Create `tests/presets/universal/test_gitignore_tracked_check.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/iorlas/Workspaces/agent-harness && uv run pytest tests/presets/universal/test_gitignore_tracked_check.py -v`
Expected: ImportError — `gitignore_tracked_check` module doesn't exist yet.

- [ ] **Step 3: Write the failing test for a tracked-but-ignored file**

Add to the same test file:

```python
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
```

- [ ] **Step 4: Write the failing test for no .gitignore (should pass, nothing to check)**

Add to the same test file:

```python
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
```

- [ ] **Step 5: Write the failing test for not a git repo (should pass gracefully)**

Add to the same test file:

```python
def test_not_a_git_repo_passes(tmp_path):
    """Not a git repo -> pass gracefully."""
    result = run_gitignore_tracked(tmp_path)
    assert result.passed
```

- [ ] **Step 6: Write minimal implementation**

Create `src/agent_harness/presets/universal/gitignore_tracked_check.py`:

```python
"""
Tracked-but-ignored file check.

WHAT: Detects files tracked by git that match .gitignore patterns.

WHY: Adding a pattern to .gitignore only prevents NEW files from being tracked.
Already-tracked files remain in the repository, invisible to developers and agents.
This is the #1 reason .DS_Store, .env backups, and build artifacts linger in repos.

WITHOUT IT: Ignored files silently stay in the repo forever. Public repos ship
OS artifacts (.DS_Store), agents commit files that should be excluded, and
.gitignore gives a false sense of cleanliness.

FIX: Run `git rm --cached <file>` for each offending file, or run `agent-harness fix`.

REQUIRES: git
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from agent_harness.runner import CheckResult


def run_gitignore_tracked(project_dir: Path) -> CheckResult:
    """Check for tracked files that match .gitignore patterns."""
    result = subprocess.run(
        ["git", "ls-files", "-ci", "--exclude-standard"],
        capture_output=True,
        text=True,
        cwd=str(project_dir),
    )
    if result.returncode != 0:
        # Not a git repo or git not available — skip gracefully
        return CheckResult(
            name="gitignore-tracked",
            passed=True,
            output="Not a git repo, skipping",
        )

    files = [f for f in result.stdout.strip().splitlines() if f]
    if not files:
        return CheckResult(
            name="gitignore-tracked",
            passed=True,
            output="No tracked files match .gitignore",
        )

    file_list = "\n  ".join(files)
    return CheckResult(
        name="gitignore-tracked",
        passed=False,
        error=(
            f"Files tracked by git but matching .gitignore:\n  {file_list}\n"
            f"Run: git rm --cached <file>  (or: agent-harness fix)"
        ),
    )
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd /Users/iorlas/Workspaces/agent-harness && uv run pytest tests/presets/universal/test_gitignore_tracked_check.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add src/agent_harness/presets/universal/gitignore_tracked_check.py tests/presets/universal/test_gitignore_tracked_check.py
git commit -m "feat: add lint check for tracked-but-ignored files"
```

---

### Task 2: Wire lint check into universal preset

**Files:**
- Modify: `src/agent_harness/presets/universal/__init__.py:13-42` (run_checks method)

- [ ] **Step 1: Write the integration — add import and call in run_checks**

In `src/agent_harness/presets/universal/__init__.py`, add the import inside `run_checks` alongside the existing lazy imports (line 16-19), and append the check to results:

```python
    def run_checks(
        self, project_dir: Path, config: dict, exclude: list[str]
    ) -> list[CheckResult]:
        from .conftest_gitignore_check import run_conftest_gitignore
        from .conftest_json_check import run_conftest_json
        from .file_length_check import run_file_length
        from .gitignore_tracked_check import run_gitignore_tracked
        from .yamllint_check import run_yamllint

        results = []
        results.append(
            run_conftest_gitignore(project_dir, stacks=config.get("stacks", set()))
        )
        results.append(run_conftest_json(project_dir, exclude_patterns=exclude))
        results.append(run_yamllint(project_dir, exclude_patterns=exclude))

        # Pass Python max_file_lines override if configured
        file_length_override = {}
        python_config = config.get("python", {})
        if isinstance(python_config, dict) and "python" in config.get("stacks", set()):
            max_file_lines = python_config.get("max_file_lines", 500)
            if max_file_lines != 500:
                file_length_override[".py"] = max_file_lines
        results.append(
            run_file_length(
                project_dir,
                max_lines_override=file_length_override or None,
                exclude_patterns=exclude,
            )
        )
        results.append(run_gitignore_tracked(project_dir))
        return results
```

- [ ] **Step 2: Run full lint to verify integration**

Run: `cd /Users/iorlas/Workspaces/agent-harness && uv run agent-harness lint`
Expected: The new `gitignore-tracked` check appears in output. It will FAIL because `src/agent_harness/policies/.DS_Store` is tracked.

- [ ] **Step 3: Commit**

```bash
git add src/agent_harness/presets/universal/__init__.py
git commit -m "feat: wire gitignore-tracked check into universal preset"
```

---

### Task 3: Fix command — git rm --cached for tracked-but-ignored files

**Files:**
- Modify: `src/agent_harness/presets/universal/__init__.py:44-45` (run_fix method)
- Create: `src/agent_harness/presets/universal/gitignore_tracked_fix.py`
- Create: `tests/presets/universal/test_gitignore_tracked_fix.py`

- [ ] **Step 1: Write the failing test**

Create `tests/presets/universal/test_gitignore_tracked_fix.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/iorlas/Workspaces/agent-harness && uv run pytest tests/presets/universal/test_gitignore_tracked_fix.py -v`
Expected: ImportError — module doesn't exist.

- [ ] **Step 3: Write minimal implementation**

Create `src/agent_harness/presets/universal/gitignore_tracked_fix.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/iorlas/Workspaces/agent-harness && uv run pytest tests/presets/universal/test_gitignore_tracked_fix.py -v`
Expected: Both tests PASS.

- [ ] **Step 5: Wire fix into universal preset**

In `src/agent_harness/presets/universal/__init__.py`, update `run_fix`:

```python
    def run_fix(self, project_dir: Path, config: dict) -> list[str]:
        from .gitignore_tracked_fix import fix_gitignore_tracked

        return fix_gitignore_tracked(project_dir)
```

- [ ] **Step 6: Run full test suite**

Run: `cd /Users/iorlas/Workspaces/agent-harness && uv run pytest -v`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/agent_harness/presets/universal/gitignore_tracked_fix.py tests/presets/universal/test_gitignore_tracked_fix.py src/agent_harness/presets/universal/__init__.py
git commit -m "feat: add fix command for tracked-but-ignored files"
```

---

### Task 4: Vendor gitignore templates

**Files:**
- Create: `src/agent_harness/templates/gitignore/Python.gitignore`
- Create: `src/agent_harness/templates/gitignore/Node.gitignore`
- Create: `src/agent_harness/templates/gitignore/macOS.gitignore`
- Create: `src/agent_harness/templates/gitignore/Windows.gitignore`
- Create: `src/agent_harness/templates/gitignore/Linux.gitignore`
- Create: `src/agent_harness/templates/gitignore/SOURCE.md`
- Create: `scripts/update-gitignore-templates.sh`

- [ ] **Step 1: Create the refresh script**

Create `scripts/update-gitignore-templates.sh`:

```bash
#!/usr/bin/env bash
# Fetch latest gitignore templates from github/gitignore.
# Run manually when templates need updating.
set -euo pipefail

DEST="src/agent_harness/templates/gitignore"
BASE="https://raw.githubusercontent.com/github/gitignore/main"

mkdir -p "$DEST"

echo "Fetching language templates..."
curl -sf "$BASE/Python.gitignore" -o "$DEST/Python.gitignore"
curl -sf "$BASE/Node.gitignore" -o "$DEST/Node.gitignore"

echo "Fetching OS globals..."
curl -sf "$BASE/Global/macOS.gitignore" -o "$DEST/macOS.gitignore"
curl -sf "$BASE/Global/Windows.gitignore" -o "$DEST/Windows.gitignore"
curl -sf "$BASE/Global/Linux.gitignore" -o "$DEST/Linux.gitignore"

echo "Done. Review changes with: git diff $DEST/"
```

- [ ] **Step 2: Run the script to vendor templates**

```bash
chmod +x scripts/update-gitignore-templates.sh
cd /Users/iorlas/Workspaces/agent-harness && bash scripts/update-gitignore-templates.sh
```

Expected: 5 template files created in `src/agent_harness/templates/gitignore/`.

- [ ] **Step 3: Create SOURCE.md attribution**

Create `src/agent_harness/templates/gitignore/SOURCE.md`:

```markdown
# Gitignore Templates

These templates are sourced from [github/gitignore](https://github.com/github/gitignore),
licensed under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/).

To update, run: `bash scripts/update-gitignore-templates.sh`
```

- [ ] **Step 4: Verify templates were fetched**

```bash
ls -la src/agent_harness/templates/gitignore/
wc -l src/agent_harness/templates/gitignore/*.gitignore
```

Expected: 5 `.gitignore` files + `SOURCE.md`, each template having 50+ lines.

- [ ] **Step 5: Commit**

```bash
git add src/agent_harness/templates/gitignore/ scripts/update-gitignore-templates.sh
git commit -m "feat: vendor gitignore templates from github/gitignore"
```

---

### Task 5: Init check — gitignore completeness

**Files:**
- Create: `src/agent_harness/presets/universal/gitignore_setup.py`
- Create: `tests/presets/universal/test_gitignore_setup.py`
- Modify: `src/agent_harness/presets/universal/__init__.py` (add run_setup)

- [ ] **Step 1: Write the failing test — missing patterns detected**

Create `tests/presets/universal/test_gitignore_setup.py`:

```python
from agent_harness.presets.universal.gitignore_setup import check_gitignore_setup


def test_missing_patterns_flagged(tmp_path):
    """Gitignore missing OS patterns -> critical issue reported."""
    (tmp_path / ".gitignore").write_text(".env\n__pycache__/\n")
    issues = check_gitignore_setup(tmp_path, stacks={"python"})
    assert len(issues) > 0
    assert any(i.severity == "critical" for i in issues)
    # Should mention .DS_Store (from macOS template)
    messages = " ".join(i.message for i in issues)
    assert ".DS_Store" in messages


def test_complete_gitignore_passes(tmp_path):
    """Gitignore with all expected patterns -> no issues."""
    # Load actual templates to build a complete .gitignore
    from agent_harness.presets.universal.gitignore_setup import _load_expected_patterns

    patterns = _load_expected_patterns({"python"})
    (tmp_path / ".gitignore").write_text("\n".join(patterns) + "\n")
    issues = check_gitignore_setup(tmp_path, stacks={"python"})
    assert issues == []


def test_no_gitignore_flagged(tmp_path):
    """No .gitignore at all -> critical issue."""
    issues = check_gitignore_setup(tmp_path, stacks=set())
    assert len(issues) == 1
    assert issues[0].severity == "critical"
    assert issues[0].fixable
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/iorlas/Workspaces/agent-harness && uv run pytest tests/presets/universal/test_gitignore_setup.py -v`
Expected: ImportError — module doesn't exist.

- [ ] **Step 3: Write the failing test — fix appends missing patterns**

Add to the same test file:

```python
def test_fix_appends_missing_patterns(tmp_path):
    """Fix should append missing patterns without removing existing ones."""
    (tmp_path / ".gitignore").write_text("# My custom rules\n.env\n")
    issues = check_gitignore_setup(tmp_path, stacks={"python"})
    fixable = [i for i in issues if i.fixable]
    assert len(fixable) > 0

    # Apply the fix
    for issue in fixable:
        issue.fix(tmp_path)

    content = (tmp_path / ".gitignore").read_text()
    # Original content preserved
    assert "# My custom rules" in content
    assert ".env" in content
    # New patterns appended
    assert ".DS_Store" in content
    assert "# Added by agent-harness" in content


def test_fix_creates_gitignore_if_missing(tmp_path):
    """Fix should create .gitignore from templates if none exists."""
    issues = check_gitignore_setup(tmp_path, stacks={"python"})
    fixable = [i for i in issues if i.fixable]
    assert len(fixable) == 1

    fixable[0].fix(tmp_path)

    content = (tmp_path / ".gitignore").read_text()
    assert ".DS_Store" in content
    assert "__pycache__" in content
```

- [ ] **Step 4: Write minimal implementation**

Create `src/agent_harness/presets/universal/gitignore_setup.py`:

```python
"""
Gitignore completeness check for init.

WHAT: Verifies .gitignore contains expected patterns for the project's tech stack
and OS globals, using vendored templates from github/gitignore.

WHY: Incomplete .gitignore files let OS artifacts (.DS_Store), build outputs, and
environment files slip into repos. Agents don't know what's missing — they need
a reference set.

FIX: Appends missing patterns in a "# Added by agent-harness" block. Never removes
or reorders existing lines.
"""

from __future__ import annotations

from pathlib import Path

from agent_harness.setup import SetupIssue

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "gitignore"

_STACK_TEMPLATES: dict[str, str] = {
    "python": "Python.gitignore",
    "javascript": "Node.gitignore",
}

_OS_TEMPLATES = ["macOS.gitignore", "Windows.gitignore", "Linux.gitignore"]


def _parse_patterns(text: str) -> set[str]:
    """Extract non-comment, non-blank lines from gitignore content."""
    patterns = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            patterns.add(stripped)
    return patterns


def _load_template(name: str) -> set[str]:
    """Load patterns from a vendored template file."""
    path = _TEMPLATES_DIR / name
    if not path.exists():
        return set()
    return _parse_patterns(path.read_text())


def _load_expected_patterns(stacks: set[str]) -> set[str]:
    """Load all expected patterns for given stacks + OS globals."""
    patterns: set[str] = set()
    for os_template in _OS_TEMPLATES:
        patterns |= _load_template(os_template)
    for stack in stacks:
        template_name = _STACK_TEMPLATES.get(stack)
        if template_name:
            patterns |= _load_template(template_name)
    return patterns


def check_gitignore_setup(
    project_dir: Path, stacks: set[str]
) -> list[SetupIssue]:
    """Check .gitignore completeness against vendored templates."""
    gitignore_path = project_dir / ".gitignore"
    expected = _load_expected_patterns(stacks)

    if not gitignore_path.exists():
        def fix_create(p: Path) -> None:
            content = "# Generated by agent-harness\n"
            for os_template in _OS_TEMPLATES:
                content += f"\n# {os_template}\n"
                path = _TEMPLATES_DIR / os_template
                if path.exists():
                    content += path.read_text().rstrip() + "\n"
            for stack in sorted(stacks):
                template_name = _STACK_TEMPLATES.get(stack)
                if template_name:
                    content += f"\n# {template_name}\n"
                    path = _TEMPLATES_DIR / template_name
                    if path.exists():
                        content += path.read_text().rstrip() + "\n"
            (p / ".gitignore").write_text(content)

        return [
            SetupIssue(
                file=".gitignore",
                message="No .gitignore found — will create from templates",
                severity="critical",
                fix=fix_create,
            )
        ]

    existing = _parse_patterns(gitignore_path.read_text())
    missing = expected - existing

    if not missing:
        return []

    missing_display = ", ".join(sorted(missing)[:10])
    more = f" (+{len(missing) - 10} more)" if len(missing) > 10 else ""

    def fix_append(p: Path) -> None:
        gitignore = p / ".gitignore"
        current = gitignore.read_text()
        if not current.endswith("\n"):
            current += "\n"
        block = "\n# Added by agent-harness\n"
        for pattern in sorted(missing):
            block += pattern + "\n"
        gitignore.write_text(current + block)

    return [
        SetupIssue(
            file=".gitignore",
            message=f"Missing {len(missing)} patterns: {missing_display}{more}",
            severity="critical",
            fix=fix_append,
        )
    ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/iorlas/Workspaces/agent-harness && uv run pytest tests/presets/universal/test_gitignore_setup.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/agent_harness/presets/universal/gitignore_setup.py tests/presets/universal/test_gitignore_setup.py
git commit -m "feat: add init check for gitignore completeness"
```

---

### Task 6: Wire setup check into universal preset

**Files:**
- Modify: `src/agent_harness/presets/universal/__init__.py` (add run_setup method)

- [ ] **Step 1: Add run_setup to UniversalPreset**

In `src/agent_harness/presets/universal/__init__.py`, add the import for `SetupIssue` at the top and the `run_setup` method:

```python
from pathlib import Path

from agent_harness.preset import Preset, PresetInfo, ToolInfo
from agent_harness.runner import CheckResult
from agent_harness.setup import SetupIssue


class UniversalPreset(Preset):
    name = "universal"

    # ... existing detect, run_checks, run_fix methods ...

    def run_setup(self, project_dir: Path, config: dict) -> list[SetupIssue]:
        from .gitignore_setup import check_gitignore_setup

        return check_gitignore_setup(
            project_dir, stacks=config.get("stacks", set())
        )

    # ... existing get_info method ...
```

- [ ] **Step 2: Run full test suite**

Run: `cd /Users/iorlas/Workspaces/agent-harness && uv run pytest -v`
Expected: All tests pass.

- [ ] **Step 3: Test init command manually**

Run: `cd /Users/iorlas/Workspaces/agent-harness && uv run agent-harness init`
Expected: The universal section shows gitignore completeness results.

- [ ] **Step 4: Commit**

```bash
git add src/agent_harness/presets/universal/__init__.py
git commit -m "feat: wire gitignore completeness check into init"
```

---

### Task 7: Fix agent-harness's own .gitignore and clean tracked files

**Files:**
- Modify: `/Users/iorlas/Workspaces/agent-harness/.gitignore`

- [ ] **Step 1: Add .DS_Store to .gitignore**

Add `.DS_Store` to the project's own `.gitignore`:

```
.env
__pycache__/
*.pyc
.venv/
*.egg-info/
dist/
build/
.coverage
coverage.xml
.worktrees/
.DS_Store
```

- [ ] **Step 2: Remove tracked .DS_Store file**

```bash
cd /Users/iorlas/Workspaces/agent-harness && git rm --cached src/agent_harness/policies/.DS_Store
```

Expected: `rm 'src/agent_harness/policies/.DS_Store'`

- [ ] **Step 3: Verify lint passes**

Run: `cd /Users/iorlas/Workspaces/agent-harness && uv run agent-harness lint`
Expected: `gitignore-tracked` check now passes.

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "fix: add .DS_Store to .gitignore and remove tracked instance"
```

---

### Task 8: Run full lint and test suite

- [ ] **Step 1: Run make lint**

Run: `cd /Users/iorlas/Workspaces/agent-harness && make lint`
Expected: All checks pass.

- [ ] **Step 2: Run make test**

Run: `cd /Users/iorlas/Workspaces/agent-harness && make test`
Expected: All tests pass, including the new ones.
