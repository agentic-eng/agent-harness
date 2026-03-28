# I0194: Dockerfile Discovery, Conftest Exceptions, Init Improvements

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace filesystem walk with git-aware file discovery, add multi-Dockerfile support with per-file conftest exceptions, fix init scaffolding for monorepos, and improve gitignore append grouping.

**Architecture:** A shared `find_files()` utility wraps `git ls-files` to discover files respecting `.gitignore`. The Docker preset uses it to find all Dockerfiles in the project tree, checking each with hadolint and conftest. Conftest exceptions are passed via `--data` (already plumbed) and guarded in every Rego policy. `detect_all` stops treating Docker-only dirs as projects.

**Tech Stack:** Python, OPA/Rego, conftest, hadolint, git

---

### Task 1: Git-aware file discovery utility

**Files:**
- Create: `src/agent_harness/git_files.py`
- Test: `tests/test_git_files.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_git_files.py
import subprocess
from agent_harness.git_files import find_files


def _init_git(path):
    """Initialize a git repo at path."""
    subprocess.run(["git", "init"], cwd=str(path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(path), capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(path), capture_output=True,
    )


def test_find_tracked_files(tmp_path):
    """Finds files that are tracked in git."""
    _init_git(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    subprocess.run(["git", "add", "Dockerfile"], cwd=str(tmp_path), capture_output=True)
    result = find_files(tmp_path, ["Dockerfile"])
    assert result == [tmp_path / "Dockerfile"]


def test_find_untracked_files(tmp_path):
    """Finds untracked files that are not gitignored."""
    _init_git(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    # Not staged, but should still be found
    result = find_files(tmp_path, ["Dockerfile"])
    assert result == [tmp_path / "Dockerfile"]


def test_skips_gitignored_files(tmp_path):
    """Does not find files matching .gitignore patterns."""
    _init_git(tmp_path)
    (tmp_path / ".gitignore").write_text("build/\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=str(tmp_path), capture_output=True)
    build = tmp_path / "build"
    build.mkdir()
    (build / "Dockerfile").write_text("FROM python:3.12")
    result = find_files(tmp_path, ["**/Dockerfile"])
    assert all("build" not in str(p) for p in result)


def test_finds_nested_files(tmp_path):
    """Finds files in subdirectories."""
    _init_git(tmp_path)
    scripts = tmp_path / "scripts" / "autonomy"
    scripts.mkdir(parents=True)
    (scripts / "Dockerfile").write_text("FROM python:3.12")
    (tmp_path / "Dockerfile").write_text("FROM node:22")
    result = find_files(tmp_path, ["**/Dockerfile", "Dockerfile"])
    paths = {str(p.relative_to(tmp_path)) for p in result}
    assert "Dockerfile" in paths
    assert "scripts/autonomy/Dockerfile" in paths


def test_returns_absolute_paths(tmp_path):
    """All returned paths are absolute."""
    _init_git(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    result = find_files(tmp_path, ["Dockerfile"])
    assert all(p.is_absolute() for p in result)


def test_fallback_without_git(tmp_path):
    """Falls back to filesystem walk when not in a git repo."""
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "Dockerfile").write_text("FROM node:22")
    result = find_files(tmp_path, ["**/Dockerfile", "Dockerfile"])
    assert len(result) >= 2


def test_find_agent_harness_ymls(tmp_path):
    """Works for non-Dockerfile patterns too."""
    _init_git(tmp_path)
    (tmp_path / ".agent-harness.yml").write_text("stacks: [python]")
    sub = tmp_path / "backend"
    sub.mkdir()
    (sub / ".agent-harness.yml").write_text("stacks: [docker]")
    result = find_files(tmp_path, ["**/.agent-harness.yml", ".agent-harness.yml"])
    assert len(result) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_git_files.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_harness.git_files'`

- [ ] **Step 3: Implement `find_files`**

```python
# src/agent_harness/git_files.py
"""Git-aware file discovery — respects .gitignore, finds tracked + untracked files."""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path


def find_files(project_dir: Path, patterns: list[str]) -> list[Path]:
    """Find files matching glob patterns, respecting .gitignore.

    Uses git ls-files for repos (tracked + untracked, excluding ignored).
    Falls back to filesystem walk for non-git directories.
    """
    files = _git_find(project_dir, patterns)
    if files is not None:
        return files
    return _fs_find(project_dir, patterns)


def _git_find(project_dir: Path, patterns: list[str]) -> list[Path] | None:
    """Use git ls-files to find files. Returns None if not in a git repo."""
    result = subprocess.run(
        [
            "git", "ls-files",
            "--cached", "--others", "--exclude-standard",
            *patterns,
        ],
        capture_output=True,
        text=True,
        cwd=str(project_dir),
    )
    if result.returncode != 0:
        return None
    paths = []
    for line in result.stdout.strip().splitlines():
        if line:
            paths.append((project_dir / line).resolve())
    return sorted(set(paths))


def _fs_find(project_dir: Path, patterns: list[str]) -> list[Path]:
    """Fallback: filesystem walk with basic glob matching."""
    _skip = {
        ".venv", "venv", "node_modules", ".git", "dist", "build",
        "__pycache__", ".astro", ".next", ".nuxt", ".worktrees",
        "_archive", ".pytest_cache", ".ruff_cache",
    }
    results: set[Path] = set()
    for path in project_dir.rglob("*"):
        if any(part in _skip for part in path.parts):
            continue
        if not path.is_file():
            continue
        rel = str(path.relative_to(project_dir))
        if any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(path.name, p) for p in patterns):
            results.add(path.resolve())
    return sorted(results)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_git_files.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent_harness/git_files.py tests/test_git_files.py
git commit -m "feat: add git-aware file discovery utility (find_files)"
```

---

### Task 2: Migrate workspace discovery to `find_files`

**Files:**
- Modify: `src/agent_harness/workspace.py`
- Modify: `tests/test_workspace.py`

- [ ] **Step 1: Update `workspace.py` to use `find_files`**

Replace the entire file content:

```python
# src/agent_harness/workspace.py
"""Workspace discovery — finds all project roots in a repo tree."""

from __future__ import annotations

from pathlib import Path

from agent_harness.git_files import find_files


def discover_roots(project_dir: Path) -> list[Path]:
    """Find directories containing .agent-harness.yml."""
    files = find_files(project_dir, ["**/.agent-harness.yml", ".agent-harness.yml"])
    return sorted({f.parent for f in files})
```

- [ ] **Step 2: Run existing workspace tests**

Run: `uv run pytest tests/test_workspace.py -v`
Expected: Most tests pass. `test_discover_skips_excluded_dirs` may need updating since git repos in tmp_path need `git init`. `test_discover_respects_max_depth` will likely fail since `find_files` has no depth limit (git doesn't need one).

- [ ] **Step 3: Update workspace tests for git-aware discovery**

The tests use `tmp_path` which is not a git repo. Since `find_files` falls back to filesystem walk for non-git dirs, existing tests should largely work. However, `test_discover_skips_excluded_dirs` tests `.venv` and `node_modules` skipping which the fallback handles. `test_discover_respects_max_depth` tested depth=4 limit which no longer applies — remove it or update to verify deep discovery works.

```python
# tests/test_workspace.py
from agent_harness.workspace import discover_roots


def test_discover_single_root(tmp_path):
    (tmp_path / ".agent-harness.yml").write_text("stacks: [python]")
    roots = discover_roots(tmp_path)
    assert roots == [tmp_path]


def test_discover_subprojects(tmp_path):
    (tmp_path / ".agent-harness.yml").write_text("stacks: [docker]")
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / ".agent-harness.yml").write_text("stacks: [python]")
    roots = discover_roots(tmp_path)
    assert tmp_path in roots
    assert backend in roots


def test_discover_skips_excluded_dirs(tmp_path):
    """Fallback fs walker skips .venv and node_modules."""
    (tmp_path / ".agent-harness.yml").write_text("stacks: [python]")
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / ".agent-harness.yml").write_text("stacks: [python]")
    node = tmp_path / "node_modules"
    node.mkdir()
    (node / ".agent-harness.yml").write_text("stacks: [javascript]")
    roots = discover_roots(tmp_path)
    assert len(roots) == 1
    assert roots[0] == tmp_path


def test_discover_nested_services(tmp_path):
    services = tmp_path / "services"
    auth = services / "auth"
    billing = services / "billing"
    auth.mkdir(parents=True)
    billing.mkdir(parents=True)
    (auth / ".agent-harness.yml").write_text("stacks: [python]")
    (billing / ".agent-harness.yml").write_text("stacks: [python]")
    roots = discover_roots(tmp_path)
    assert auth in roots
    assert billing in roots


def test_discover_no_dotfiles(tmp_path):
    roots = discover_roots(tmp_path)
    assert roots == []
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_workspace.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent_harness/workspace.py tests/test_workspace.py
git commit -m "refactor: migrate workspace discovery to git-aware find_files"
```

---

### Task 3: Migrate `detect_all` to `find_files` and filter Docker-only dirs

**Files:**
- Modify: `src/agent_harness/detect.py`
- Modify: `tests/test_detect.py`

- [ ] **Step 1: Write new test for Docker-only dir filtering**

Add to `tests/test_detect.py`:

```python
def test_detect_all_excludes_docker_only_dirs(tmp_path):
    """Dirs with only Dockerfiles are not detected as projects."""
    from agent_harness.detect import detect_all

    # Root has a pyproject.toml + Dockerfile
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")

    # scripts/autonomy has ONLY a Dockerfile — not a project
    scripts = tmp_path / "scripts" / "autonomy"
    scripts.mkdir(parents=True)
    (scripts / "Dockerfile").write_text("FROM python:3.12")

    results = detect_all(tmp_path)
    assert tmp_path in results
    assert scripts not in results


def test_detect_all_includes_dir_with_manifest(tmp_path):
    """Dirs with dependency manifests ARE detected as projects."""
    from agent_harness.detect import detect_all

    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "pyproject.toml").write_text("[project]\nname='x'")
    (backend / "Dockerfile").write_text("FROM python:3.12")

    results = detect_all(tmp_path)
    assert backend in results
    assert "python" in results[backend]
    assert "docker" in results[backend]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_detect.py::test_detect_all_excludes_docker_only_dirs -v`
Expected: FAIL — scripts dir is currently detected as a project

- [ ] **Step 3: Update `detect.py`**

Replace the entire file:

```python
# src/agent_harness/detect.py
"""Stack detection orchestrator — delegates to preset detect methods."""

from __future__ import annotations

from pathlib import Path

from agent_harness.git_files import find_files
from agent_harness.registry import PRESETS

# Dependency manifests that define a real project (not just a build target)
_PROJECT_MANIFESTS = [
    "pyproject.toml", "package.json", "go.mod", "Cargo.toml",
    "Gemfile", "composer.json", "pom.xml", "build.gradle",
]


def detect_stacks(project_dir: Path) -> set[str]:
    """Detect which stacks a project uses based on file presence."""
    return {p.name for p in PRESETS if p.detect(project_dir)}


def detect_all(project_dir: Path) -> dict[Path, set[str]]:
    """Detect stacks in root and subdirectories.

    A directory is a project only if it has a dependency manifest
    (pyproject.toml, package.json, etc.) or is the root directory.
    Docker-only directories are build targets, not projects.
    """
    # Find all manifest files + Docker indicators
    all_patterns = [f"**/{m}" for m in _PROJECT_MANIFESTS] + [m for m in _PROJECT_MANIFESTS]
    manifest_files = find_files(project_dir, all_patterns)

    # Directories that have a real project manifest
    project_dirs: set[Path] = set()
    for f in manifest_files:
        project_dirs.add(f.parent)

    # Always include root if it has any stacks
    root_stacks = detect_stacks(project_dir)
    if root_stacks:
        project_dirs.add(project_dir)

    # Detect stacks only in real project directories
    results: dict[Path, set[str]] = {}
    for d in sorted(project_dirs):
        stacks = detect_stacks(d)
        if stacks:
            results[d] = stacks

    return results
```

- [ ] **Step 4: Run all detect tests**

Run: `uv run pytest tests/test_detect.py -v`
Expected: All pass. Note: `test_detect_all_subprojects` has a root dir with only a Dockerfile — that's the root, so it should still be included. Verify this.

- [ ] **Step 5: If `test_detect_all_subprojects` fails, update it**

The existing test creates root with only a Dockerfile (no manifest). With the new logic, root is included if it has any stacks. Check behavior and update test expectations if needed:

```python
def test_detect_all_subprojects(tmp_path):
    """Root with Docker + subprojects with manifests."""
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "pyproject.toml").write_text("[project]\nname='x'")
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text('{"name":"y"}')
    from agent_harness.detect import detect_all

    results = detect_all(tmp_path)
    assert "docker" in results[tmp_path]
    assert "python" in results[backend]
    assert "javascript" in results[frontend]
```

- [ ] **Step 6: Commit**

```bash
git add src/agent_harness/detect.py tests/test_detect.py
git commit -m "refactor: detect_all uses find_files, filters Docker-only dirs"
```

---

### Task 4: Multi-Dockerfile discovery in Docker preset

**Files:**
- Modify: `src/agent_harness/presets/docker/detect.py`
- Create: `tests/presets/docker/test_find_dockerfiles.py`

- [ ] **Step 1: Write failing test**

```python
# tests/presets/docker/test_find_dockerfiles.py
import subprocess

from agent_harness.presets.docker.detect import find_dockerfiles


def _init_git(path):
    subprocess.run(["git", "init"], cwd=str(path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(path), capture_output=True)


def test_finds_root_dockerfile(tmp_path):
    _init_git(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    result = find_dockerfiles(tmp_path)
    assert len(result) == 1
    assert result[0].name == "Dockerfile"


def test_finds_nested_dockerfiles(tmp_path):
    _init_git(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    scripts = tmp_path / "scripts" / "autonomy"
    scripts.mkdir(parents=True)
    (scripts / "Dockerfile").write_text("FROM node:22")
    infra = tmp_path / "infrastructure" / "staging"
    infra.mkdir(parents=True)
    (infra / "Dockerfile").write_text("FROM nginx:1.27")
    result = find_dockerfiles(tmp_path)
    assert len(result) == 3


def test_returns_relative_paths(tmp_path):
    _init_git(tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "Dockerfile").write_text("FROM python:3.12")
    result = find_dockerfiles(tmp_path)
    # Should return paths relative to project_dir
    assert result[0] == Path("scripts/Dockerfile")


def test_no_dockerfiles(tmp_path):
    _init_git(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    result = find_dockerfiles(tmp_path)
    assert result == []
```

Add this import at top of test file:
```python
from pathlib import Path
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/presets/docker/test_find_dockerfiles.py -v`
Expected: FAIL — `ImportError: cannot import name 'find_dockerfiles'`

- [ ] **Step 3: Implement `find_dockerfiles`**

Update `src/agent_harness/presets/docker/detect.py`:

```python
# src/agent_harness/presets/docker/detect.py
"""Detect whether a project uses the Docker stack."""

from __future__ import annotations

from pathlib import Path

from agent_harness.git_files import find_files

DOCKER_INDICATORS = ["Dockerfile", "docker-compose.prod.yml", "docker-compose.yml"]


def detect_docker(project_dir: Path) -> bool:
    """Return True if the project contains Docker stack indicators."""
    return any((project_dir / f).is_file() for f in DOCKER_INDICATORS)


def find_dockerfiles(project_dir: Path) -> list[Path]:
    """Find all Dockerfiles in the project tree, as relative paths."""
    abs_paths = find_files(project_dir, ["**/Dockerfile", "Dockerfile", "**/Dockerfile.*", "Dockerfile.*"])
    return sorted(p.relative_to(project_dir) for p in abs_paths)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/presets/docker/test_find_dockerfiles.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent_harness/presets/docker/detect.py tests/presets/docker/test_find_dockerfiles.py
git commit -m "feat: add find_dockerfiles for multi-Dockerfile discovery"
```

---

### Task 5: Multi-Dockerfile hadolint check

**Files:**
- Modify: `src/agent_harness/presets/docker/hadolint_check.py`

- [ ] **Step 1: Update hadolint to accept a list of Dockerfiles**

```python
# src/agent_harness/presets/docker/hadolint_check.py
"""
Hadolint Dockerfile linter check.

WHAT: Runs hadolint on all Dockerfiles in the project tree.

WHY: Hadolint is a Dockerfile-specific linter that catches best-practice
violations (DL/SC rules) that conftest policies don't cover — apt-get without
--no-install-recommends, missing cleanup in the same layer, shell form vs exec
form, and dozens more. It's the shellcheck equivalent for Dockerfiles.

WITHOUT IT: Subtle Dockerfile anti-patterns accumulate: bloated images from
missing cleanup, security issues from shell form CMD, and non-reproducible
builds from unpinned apt packages.

FIX: Read hadolint's rule output (DLxxxx / SCxxxx) and apply the suggested fix.
Most rules have a --ignore flag if intentionally skipped.

REQUIRES: hadolint (via PATH)
"""

from __future__ import annotations

from pathlib import Path

from agent_harness.runner import CheckResult, run_check


def run_hadolint(project_dir: Path, dockerfiles: list[Path] | None = None) -> list[CheckResult]:
    """Run hadolint on discovered Dockerfiles. Returns one result per file."""
    if dockerfiles is None:
        # Legacy single-file mode
        dockerfile = project_dir / "Dockerfile"
        if not dockerfile.exists():
            return [CheckResult(name="hadolint", passed=True, output="No Dockerfile, skipping")]
        return [run_check("hadolint", ["hadolint", str(dockerfile)], cwd=str(project_dir))]

    if not dockerfiles:
        return [CheckResult(name="hadolint", passed=True, output="No Dockerfiles found")]

    results = []
    for rel_path in dockerfiles:
        abs_path = project_dir / rel_path
        name = f"hadolint:{rel_path}" if str(rel_path) != "Dockerfile" else "hadolint"
        results.append(run_check(name, ["hadolint", str(abs_path)], cwd=str(project_dir)))
    return results
```

- [ ] **Step 2: Run existing hadolint-related tests (if any) plus full suite**

Run: `uv run pytest tests/ -v -k hadolint`
Expected: No existing tests break (there are no dedicated hadolint tests — it's tested via integration)

- [ ] **Step 3: Commit**

```bash
git add src/agent_harness/presets/docker/hadolint_check.py
git commit -m "feat: hadolint checks all discovered Dockerfiles"
```

---

### Task 6: Conftest exceptions in Rego policies

**Files:**
- Modify: `src/agent_harness/policies/dockerfile/user.rego`
- Modify: `src/agent_harness/policies/dockerfile/healthcheck.rego`
- Modify: `src/agent_harness/policies/dockerfile/cache.rego`
- Modify: `src/agent_harness/policies/dockerfile/secrets.rego`
- Modify: `src/agent_harness/policies/dockerfile/layers.rego`
- Modify: `src/agent_harness/policies/dockerfile/base_image.rego`
- Modify: `src/agent_harness/policies/dockerfile/user_test.rego`
- Modify: all other `_test.rego` files in dockerfile/

- [ ] **Step 1: Update `user.rego` with exceptions guard**

```rego
package dockerfile.user

# USER INSTRUCTION — no running as root
#
# WHAT: Ensures at least one USER instruction exists so the container
# does not run as root.
#
# WHY: Agents generate Dockerfiles that run as root by default. A container
# escape vulnerability gives the attacker root on the host. CIS Docker
# Benchmark 4.1 requires non-root users.
#
# WITHOUT IT: Containers run as root — one exploit away from full host
# compromise. Every security scanner will flag it.
#
# FIX: Add `USER nonroot` (or another non-root user) near the end of
# the Dockerfile, after installing dependencies.
#
# Input: flat array of Dockerfile instructions [{Cmd, Flags, Value, Stage}, ...]

import rego.v1

# ── Exceptions: skip if listed in data.exceptions ──

default _exceptions := []

_exceptions := data.exceptions if {
	data.exceptions
}

# ── Policy: must have USER instruction ──

deny contains msg if {
	not "dockerfile.user" in _exceptions
	not _has_user_instruction
	msg := "Dockerfile has no USER instruction — containers should not run as root. Add 'USER nonroot' or similar."
}

_has_user_instruction if {
	some instr in input
	instr.Cmd == "user"
}
```

- [ ] **Step 2: Update `user_test.rego` with exception test**

```rego
package dockerfile.user_test

import rego.v1

import data.dockerfile.user

# ── DENY: no USER instruction ──

test_missing_user_fires if {
	user.deny with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "run", "Value": ["uv sync"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── PASS: USER instruction present ──

test_with_user_passes if {
	count(user.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "user", "Value": ["nonroot"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── PASS: exception skips the check ──

test_exception_skips_user_check if {
	count(user.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "run", "Value": ["uv sync"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
		with data.exceptions as ["dockerfile.user"]
}
```

- [ ] **Step 3: Update `healthcheck.rego`**

Add after the existing `import rego.v1`:

```rego
# ── Exceptions: skip if listed in data.exceptions ──

default _exceptions := []

_exceptions := data.exceptions if {
	data.exceptions
}
```

Update the deny rule:

```rego
deny contains msg if {
	not "dockerfile.healthcheck" in _exceptions
	not _has_healthcheck
	msg := "Dockerfile has no HEALTHCHECK instruction — orchestrators can't detect unhealthy containers. Add 'HEALTHCHECK CMD curl -f http://localhost/ || exit 1' or similar."
}
```

- [ ] **Step 4: Update `healthcheck_test.rego` — add exception test**

Add at the end:

```rego
# ── PASS: exception skips the check ──

test_exception_skips_healthcheck if {
	count(healthcheck.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
		with data.exceptions as ["dockerfile.healthcheck"]
}
```

- [ ] **Step 5: Update `cache.rego`**

Add the exceptions block after `import rego.v1`:

```rego
default _exceptions := []

_exceptions := data.exceptions if {
	data.exceptions
}
```

Update the deny rule — add `not "dockerfile.cache" in _exceptions` as the first condition:

```rego
deny contains msg if {
	not "dockerfile.cache" in _exceptions
	some instr in input
	instr.Cmd == "run"
	# ... rest unchanged
```

- [ ] **Step 6: Update `cache_test.rego` — add exception test**

Add at end (read the existing test file first to match its import pattern):

```rego
test_exception_skips_cache if {
	count(cache.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "run", "Value": ["pip install -r requirements.txt"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
		with data.exceptions as ["dockerfile.cache"]
}
```

- [ ] **Step 7: Update `secrets.rego`**

Add the exceptions block after `import rego.v1`:

```rego
default _exceptions := []

_exceptions := data.exceptions if {
	data.exceptions
}
```

Update both deny rules — add `not "dockerfile.secrets" in _exceptions` as the first condition in each.

- [ ] **Step 8: Update `secrets_test.rego` — add exception test**

```rego
test_exception_skips_secrets if {
	count(secrets.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "env", "Value": ["API_KEY=hunter2"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
		with data.exceptions as ["dockerfile.secrets"]
}
```

- [ ] **Step 9: Update `layers.rego`**

Add exceptions block after `import rego.v1`. Update deny rule with `not "dockerfile.layers" in _exceptions` guard.

- [ ] **Step 10: Update `layers_test.rego` — add exception test**

```rego
test_exception_skips_layers if {
	count(layers.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "copy", "Value": [".", "."], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "run", "Value": ["pip install -r requirements.txt"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
		with data.exceptions as ["dockerfile.layers"]
}
```

- [ ] **Step 11: Update `base_image.rego`**

Add exceptions block after `import rego.v1`. Update deny rule with `not "dockerfile.base_image" in _exceptions` guard.

- [ ] **Step 12: Update `base_image_test.rego` — add exception test**

```rego
test_exception_skips_base_image if {
	count(base_image.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["python:3.12-alpine"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
		with data.exceptions as ["dockerfile.base_image"]
}
```

- [ ] **Step 13: Run all Rego tests**

Run: `conftest verify --policy src/agent_harness/policies/dockerfile/`
Expected: All tests pass

- [ ] **Step 14: Commit**

```bash
git add src/agent_harness/policies/dockerfile/
git commit -m "feat: add conftest exceptions guard to all Dockerfile Rego policies"
```

---

### Task 7: Conftest exceptions in compose and dokploy Rego policies

**Files:**
- Modify: `src/agent_harness/policies/compose/services.rego`
- Modify: `src/agent_harness/policies/compose/images.rego`
- Modify: `src/agent_harness/policies/compose/escaping.rego`
- Modify: `src/agent_harness/policies/compose/hostname.rego`
- Modify: `src/agent_harness/policies/compose/volumes.rego`
- Modify: `src/agent_harness/policies/compose/configs.rego`
- Modify: `src/agent_harness/policies/dokploy/traefik.rego`
- Modify: All corresponding `_test.rego` files

- [ ] **Step 1: Add exceptions guard to all compose policies**

For each compose policy file (`services.rego`, `images.rego`, `escaping.rego`, `hostname.rego`, `volumes.rego`, `configs.rego`), add after `import rego.v1`:

```rego
default _exceptions := []

_exceptions := data.exceptions if {
	data.exceptions
}
```

And add `not "<package_name>" in _exceptions` as the first condition in each `deny` rule. The exception IDs are:

| File | Exception ID(s) |
|------|----------------|
| `services.rego` | `compose.services_healthcheck`, `compose.services_restart`, `compose.services_ports` |
| `images.rego` | `compose.images_build`, `compose.images_mutable_tag`, `compose.images_implicit_latest`, `compose.images_pin_own` |
| `escaping.rego` | `compose.escaping` |
| `hostname.rego` | `compose.hostname` |
| `volumes.rego` | `compose.volumes` |
| `configs.rego` | `compose.configs` |

For policies with multiple deny rules (like `services.rego` and `images.rego`), each deny rule gets its own exception ID so they can be individually skipped. The pattern is `<package>.<rule_purpose>`.

Example for `services.rego` healthcheck deny:
```rego
deny contains msg if {
	not "compose.services_healthcheck" in _exceptions
	some name, svc in input.services
	# ... rest unchanged
```

Example for `services.rego` restart deny:
```rego
deny contains msg if {
	not "compose.services_restart" in _exceptions
	some name, svc in input.services
	# ... rest unchanged
```

Example for `services.rego` ports deny:
```rego
deny contains msg if {
	not "compose.services_ports" in _exceptions
	some name, svc in input.services
	# ... rest unchanged
```

- [ ] **Step 2: Add exceptions guard to `dokploy/traefik.rego`**

Add the exceptions block. The two deny rules get IDs `dokploy.traefik_enable` and `dokploy.traefik_network`.

- [ ] **Step 3: Add exception tests to all `_test.rego` files**

For each test file, add one test per deny rule that verifies the exception skips it. Pattern:

```rego
test_exception_skips_<rule> if {
	count(<policy>.deny) == 0 with input as <bad_input>
		with data.exceptions as ["<exception_id>"]
}
```

Use the existing bad input from the `test_*_fires` tests as the input for exception tests.

- [ ] **Step 4: Run all Rego tests**

Run:
```bash
conftest verify --policy src/agent_harness/policies/compose/
conftest verify --policy src/agent_harness/policies/dokploy/
```
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add src/agent_harness/policies/compose/ src/agent_harness/policies/dokploy/
git commit -m "feat: add conftest exceptions guard to compose and dokploy Rego policies"
```

---

### Task 8: Wire multi-Dockerfile + exceptions into Docker preset

**Files:**
- Modify: `src/agent_harness/presets/docker/__init__.py`
- Modify: `src/agent_harness/presets/docker/conftest_dockerfile_check.py`
- Modify: `tests/presets/docker/test_conftest_dockerfile_check.py`

- [ ] **Step 1: Update `conftest_dockerfile_check.py` to accept Dockerfiles + skip config**

```python
# src/agent_harness/presets/docker/conftest_dockerfile_check.py
"""
Conftest Dockerfile check.

WHAT: Runs conftest on all Dockerfiles with bundled policies covering base image
selection, cache mounts, healthchecks, layer ordering, secrets, and non-root user.

WHY: Agents generate Dockerfiles that run as root, skip healthchecks, use Alpine
with musl-sensitive stacks, hardcode secrets in ENV/ARG, and bust cache by copying
source before dependencies. Each of these is a production incident waiting to happen.

WITHOUT IT: Containers run as root (one exploit = host compromise), orchestrators
can't detect unhealthy containers, 5-minute builds that should take 10 seconds,
and secrets leaked in image layers.

FIX: Read the specific conftest violation messages — each maps to a concrete
Dockerfile change (add USER, add HEALTHCHECK, reorder COPY layers, etc.).

REQUIRES: conftest (via PATH)
"""

from __future__ import annotations

from pathlib import Path

from agent_harness.conftest import run_conftest as _run_conftest
from agent_harness.runner import CheckResult


def run_conftest_dockerfile(
    project_dir: Path,
    dockerfiles: list[Path] | None = None,
    conftest_skip: dict[str, list[str]] | None = None,
) -> list[CheckResult]:
    """Run conftest on Dockerfiles with bundled dockerfile policies.

    Args:
        project_dir: Project root directory.
        dockerfiles: Relative paths to Dockerfiles. If None, checks project_dir/Dockerfile.
        conftest_skip: Map of relative Dockerfile path -> list of policy IDs to skip.
    """
    if conftest_skip is None:
        conftest_skip = {}

    if dockerfiles is None:
        # Legacy single-file mode
        skip = conftest_skip.get("Dockerfile", [])
        data = {"exceptions": skip} if skip else None
        return [_run_conftest("conftest-dockerfile", project_dir, "Dockerfile", "dockerfile", data=data)]

    if not dockerfiles:
        return [CheckResult(name="conftest-dockerfile", passed=True, output="No Dockerfiles found")]

    results = []
    for rel_path in dockerfiles:
        skip = conftest_skip.get(str(rel_path), [])
        data = {"exceptions": skip} if skip else None
        name = f"conftest-dockerfile:{rel_path}" if str(rel_path) != "Dockerfile" else "conftest-dockerfile"
        results.append(_run_conftest(name, project_dir, str(rel_path), "dockerfile", data=data))
    return results
```

- [ ] **Step 2: Update `DockerPreset.__init__.py` to wire discovery + config**

```python
# src/agent_harness/presets/docker/__init__.py
from pathlib import Path

from agent_harness.preset import Preset, PresetInfo, ToolInfo
from agent_harness.runner import CheckResult


class DockerPreset(Preset):
    name = "docker"

    def detect(self, project_dir: Path) -> bool:
        from .detect import detect_docker

        return detect_docker(project_dir)

    def run_checks(
        self, project_dir: Path, config: dict, exclude: list[str]
    ) -> list[CheckResult]:
        from .conftest_compose_check import run_conftest_compose
        from .conftest_dockerfile_check import run_conftest_dockerfile
        from .detect import find_dockerfiles
        from .hadolint_check import run_hadolint

        docker_config = config.get("docker", {})
        conftest_skip = docker_config.get("conftest_skip", {})

        # Discover all Dockerfiles in the project tree
        dockerfiles = find_dockerfiles(project_dir)

        results: list[CheckResult] = []
        results.extend(run_conftest_dockerfile(project_dir, dockerfiles, conftest_skip))
        results.append(
            run_conftest_compose(
                project_dir, docker_config.get("own_image_prefix", "")
            )
        )
        results.extend(run_hadolint(project_dir, dockerfiles))
        return results

    def run_fix(self, project_dir: Path, config: dict) -> list[str]:
        return []

    def get_info(self) -> PresetInfo:
        return PresetInfo(
            name="docker",
            tools=[
                ToolInfo(
                    "hadolint",
                    "Dockerfile best practices",
                    "hadolint",
                    "brew install hadolint",
                ),
                ToolInfo(
                    "conftest",
                    "compose healthchecks, image pinning, ports",
                    "conftest",
                    "brew install conftest",
                ),
            ],
        )
```

- [ ] **Step 3: Update test file**

```python
# tests/presets/docker/test_conftest_dockerfile_check.py
from pathlib import Path

from agent_harness.presets.docker.conftest_dockerfile_check import (
    run_conftest_dockerfile,
)

_GOOD_DOCKERFILE = (
    "FROM python:3.12-bookworm-slim\nWORKDIR /app\n"
    "COPY pyproject.toml uv.lock ./\n"
    "RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev\n"
    "COPY src/ ./src/\nUSER nonroot\n"
    "HEALTHCHECK CMD curl -f http://localhost/ || exit 1\n"
)

_BAD_NO_USER = (
    "FROM python:3.12-bookworm-slim\nWORKDIR /app\nCOPY . .\n"
    "RUN uv sync\nHEALTHCHECK CMD curl -f http://localhost/ || exit 1\n"
)


def test_conftest_dockerfile_good(tmp_path):
    (tmp_path / "Dockerfile").write_text(_GOOD_DOCKERFILE)
    results = run_conftest_dockerfile(tmp_path)
    assert all(r.passed for r in results), f"Expected pass but got: {[r.error for r in results]}"


def test_conftest_dockerfile_bad_no_user(tmp_path):
    (tmp_path / "Dockerfile").write_text(_BAD_NO_USER)
    results = run_conftest_dockerfile(tmp_path)
    assert any(not r.passed for r in results)


def test_conftest_no_dockerfile(tmp_path):
    results = run_conftest_dockerfile(tmp_path)
    assert all(r.passed for r in results)  # graceful skip


def test_conftest_multi_dockerfile(tmp_path):
    """Checks multiple Dockerfiles when given a list."""
    (tmp_path / "Dockerfile").write_text(_GOOD_DOCKERFILE)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "Dockerfile").write_text(_BAD_NO_USER)

    results = run_conftest_dockerfile(
        tmp_path,
        dockerfiles=[Path("Dockerfile"), Path("scripts/Dockerfile")],
    )
    assert len(results) == 2
    # Root Dockerfile is good
    root_result = [r for r in results if r.name == "conftest-dockerfile"][0]
    assert root_result.passed
    # scripts/Dockerfile is bad (no user)
    sub_result = [r for r in results if "scripts" in r.name][0]
    assert not sub_result.passed


def test_conftest_skip_exception(tmp_path):
    """conftest_skip suppresses specific policy violations."""
    (tmp_path / "Dockerfile").write_text(_BAD_NO_USER)
    results = run_conftest_dockerfile(
        tmp_path,
        dockerfiles=[Path("Dockerfile")],
        conftest_skip={"Dockerfile": ["dockerfile.user", "dockerfile.layers", "dockerfile.cache"]},
    )
    assert all(r.passed for r in results)


def test_conftest_skip_per_file(tmp_path):
    """Different skip lists per Dockerfile path."""
    (tmp_path / "Dockerfile").write_text(_GOOD_DOCKERFILE)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "Dockerfile").write_text(_BAD_NO_USER)

    results = run_conftest_dockerfile(
        tmp_path,
        dockerfiles=[Path("Dockerfile"), Path("scripts/Dockerfile")],
        conftest_skip={
            "scripts/Dockerfile": ["dockerfile.user", "dockerfile.layers", "dockerfile.cache"],
        },
    )
    assert all(r.passed for r in results)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/presets/docker/test_conftest_dockerfile_check.py -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/agent_harness/presets/docker/ tests/presets/docker/
git commit -m "feat: wire multi-Dockerfile discovery + conftest exceptions into Docker preset"
```

---

### Task 9: Conftest exceptions for compose and dokploy presets

**Files:**
- Modify: `src/agent_harness/presets/docker/conftest_compose_check.py`
- Modify: `src/agent_harness/presets/dokploy/__init__.py`
- Modify: `src/agent_harness/presets/dokploy/conftest_dokploy_check.py`

- [ ] **Step 1: Update `conftest_compose_check.py` to accept skip config**

```python
# src/agent_harness/presets/docker/conftest_compose_check.py
"""
Conftest docker-compose check.

WHAT: Runs conftest on docker-compose.prod.yml with bundled compose policies
covering dollar escaping, hostname requirements, image pinning, healthchecks,
restart policies, and port binding safety.

WHY: Agents generate compose files with bare $ in passwords (silently corrupted
by interpolation), missing healthchecks (load balancers route to dead containers),
no restart policies (crashed services stay down), and 0.0.0.0 port bindings
(bypasses host firewall, exposes internal services to the internet).

WITHOUT IT: Passwords silently corrupted, silent outages from unhealthy containers,
permanent crashes, and accidentally internet-exposed internal services.

FIX: Read the specific conftest violation messages — each maps to a concrete
compose file change (escape $$, add healthcheck, add restart policy, bind to
127.0.0.1).

REQUIRES: conftest (via PATH)
"""

from __future__ import annotations

from pathlib import Path

from agent_harness.conftest import run_conftest as _run_conftest
from agent_harness.runner import CheckResult


def run_conftest_compose(
    project_dir: Path,
    own_image_prefix: str = "",
    conftest_skip: dict[str, list[str]] | None = None,
) -> CheckResult:
    """Run conftest on docker-compose.prod.yml with bundled compose policies."""
    if conftest_skip is None:
        conftest_skip = {}

    target = "docker-compose.prod.yml"
    skip = conftest_skip.get(target, [])

    data: dict | None = {}
    if own_image_prefix:
        data["own_image_prefix"] = own_image_prefix
    if skip:
        data["exceptions"] = skip
    if not data:
        data = None

    return _run_conftest("conftest-compose", project_dir, target, "compose", data=data)
```

- [ ] **Step 2: Update `DockerPreset.run_checks` to pass skip config to compose**

In `src/agent_harness/presets/docker/__init__.py`, update the compose call:

```python
        results.append(
            run_conftest_compose(
                project_dir,
                docker_config.get("own_image_prefix", ""),
                conftest_skip,
            )
        )
```

- [ ] **Step 3: Update `conftest_dokploy_check.py` to accept skip config**

```python
# src/agent_harness/presets/dokploy/conftest_dokploy_check.py
"""
Conftest Dokploy check.

WHAT: Runs conftest on docker-compose files with bundled Dokploy policies
covering Traefik label requirements and network attachment.

WHY: Agents add Traefik routing labels but forget `traefik.enable=true`
(silent 404 — traefik-ts has exposedbydefault=false) or forget to attach
services to `dokploy-network` (silent 502 — Traefik can't reach the service).

WITHOUT IT: Silent 404s and 502s that take hours to debug because the
labels "look correct."

FIX: Read the specific conftest violation messages — each maps to a concrete
compose file change (add `traefik.enable=true`, add `dokploy-network`).

REQUIRES: conftest (via PATH)
"""

from __future__ import annotations

from pathlib import Path

from agent_harness.conftest import run_conftest as _run_conftest
from agent_harness.runner import CheckResult

COMPOSE_FILES = ["docker-compose.prod.yml", "docker-compose.yml"]


def run_conftest_dokploy(project_dir: Path, conftest_skip: dict[str, list[str]] | None = None) -> CheckResult:
    """Run conftest on compose files with bundled Dokploy policies."""
    if conftest_skip is None:
        conftest_skip = {}

    name = "conftest-dokploy"
    for f in COMPOSE_FILES:
        target = project_dir / f
        if target.exists():
            skip = conftest_skip.get(f, [])
            data = {"exceptions": skip} if skip else None
            return _run_conftest(name, project_dir, f, "dokploy", data=data)

    return CheckResult(
        name=name,
        passed=True,
        output=f"Skipping {name}: no compose file found",
    )
```

- [ ] **Step 4: Update `DokployPreset` to pass config**

```python
# src/agent_harness/presets/dokploy/__init__.py
from pathlib import Path

from agent_harness.preset import Preset, PresetInfo, ToolInfo
from agent_harness.runner import CheckResult


class DokployPreset(Preset):
    name = "dokploy"

    def detect(self, project_dir: Path) -> bool:
        from .detect import detect_dokploy

        return detect_dokploy(project_dir)

    def run_checks(
        self, project_dir: Path, config: dict, exclude: list[str]
    ) -> list[CheckResult]:
        from .conftest_dokploy_check import run_conftest_dokploy

        dokploy_config = config.get("dokploy", {})
        conftest_skip = dokploy_config.get("conftest_skip", {})
        return [run_conftest_dokploy(project_dir, conftest_skip)]

    def run_fix(self, project_dir: Path, config: dict) -> list[str]:
        return []

    def get_info(self) -> PresetInfo:
        return PresetInfo(
            name="dokploy",
            tools=[
                ToolInfo(
                    "conftest",
                    "traefik.enable, dokploy-network",
                    "conftest",
                    "brew install conftest",
                ),
            ],
        )
```

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/agent_harness/presets/docker/conftest_compose_check.py src/agent_harness/presets/docker/__init__.py src/agent_harness/presets/dokploy/
git commit -m "feat: conftest exceptions for compose and dokploy presets"
```

---

### Task 10: Gitignore grouped append

**Files:**
- Modify: `src/agent_harness/presets/universal/gitignore_setup.py`
- Modify: `tests/presets/universal/test_gitignore_setup.py`

- [ ] **Step 1: Write failing test for grouped append**

Add to `tests/presets/universal/test_gitignore_setup.py`:

```python
def test_fix_appends_grouped_by_template(tmp_path):
    """Fix should group appended patterns by source template, not one flat block."""
    (tmp_path / ".gitignore").write_text("# My rules\n.env\n")
    issues = check_gitignore_setup(tmp_path, stacks={"python"})
    fixable = [i for i in issues if i.fixable]
    assert len(fixable) > 0

    for issue in fixable:
        assert issue.fix is not None
        issue.fix(tmp_path)

    content = (tmp_path / ".gitignore").read_text()
    # Should have category headers, not one flat "Added by agent-harness" block
    assert "# Python (added by agent-harness)" in content or "# Python.gitignore (added by agent-harness)" in content
    assert "# macOS" in content or "# macOS.gitignore" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/presets/universal/test_gitignore_setup.py::test_fix_appends_grouped_by_template -v`
Expected: FAIL — currently writes one flat `# Added by agent-harness` block

- [ ] **Step 3: Update `gitignore_setup.py` fix to group by template**

Replace the `fix_append` closure in `check_gitignore_setup`:

```python
    def fix_append(p: Path) -> None:
        current = gitignore_path.read_text()
        if not current.endswith("\n"):
            current += "\n"

        # Group missing patterns by their source template
        block = ""
        for os_template in _OS_TEMPLATES:
            template_patterns = _load_template(os_template)
            template_missing = missing & template_patterns
            if template_missing:
                label = os_template.replace(".gitignore", "")
                block += f"\n# {label} (added by agent-harness)\n"
                for pattern in sorted(template_missing):
                    block += pattern + "\n"

        for stack in sorted(stacks):
            template_name = _STACK_TEMPLATES.get(stack)
            if template_name:
                template_patterns = _load_template(template_name)
                template_missing = missing & template_patterns
                if template_missing:
                    label = template_name.replace(".gitignore", "")
                    block += f"\n# {label} (added by agent-harness)\n"
                    for pattern in sorted(template_missing):
                        block += pattern + "\n"

        # Catch any patterns not covered by templates
        accounted = set()
        for os_template in _OS_TEMPLATES:
            accounted |= _load_template(os_template)
        for stack in stacks:
            template_name = _STACK_TEMPLATES.get(stack)
            if template_name:
                accounted |= _load_template(template_name)
        uncategorized = missing - accounted
        if uncategorized:
            block += "\n# Other (added by agent-harness)\n"
            for pattern in sorted(uncategorized):
                block += pattern + "\n"

        gitignore_path.write_text(current + block)
```

- [ ] **Step 4: Update existing test assertion**

The `test_fix_appends_missing_patterns` test asserts `"# Added by agent-harness" in content`. Update it to check for the new grouped format:

```python
def test_fix_appends_missing_patterns(tmp_path):
    """Fix should append missing patterns without removing existing ones."""
    (tmp_path / ".gitignore").write_text("# My custom rules\n.env\n")
    issues = check_gitignore_setup(tmp_path, stacks={"python"})
    fixable = [i for i in issues if i.fixable]
    assert len(fixable) > 0

    for issue in fixable:
        assert issue.fix is not None
        issue.fix(tmp_path)

    content = (tmp_path / ".gitignore").read_text()
    # Original content preserved
    assert "# My custom rules" in content
    assert ".env" in content
    # New patterns appended with category grouping
    assert ".DS_Store" in content
    assert "(added by agent-harness)" in content
```

- [ ] **Step 5: Run all gitignore tests**

Run: `uv run pytest tests/presets/universal/test_gitignore_setup.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/agent_harness/presets/universal/gitignore_setup.py tests/presets/universal/test_gitignore_setup.py
git commit -m "feat: group gitignore additions by source template"
```

---

### Task 11: Init scaffold fix for monorepo subprojects

**Files:**
- Modify: `src/agent_harness/init/scaffold.py`

- [ ] **Step 1: Update `scaffold_project` to skip project-level files for non-root dirs**

In `scaffold_project`, after determining the files dict, filter based on whether this is a subproject. The function receives `project_dir` — compare it to `git_root` from config:

Add this after line 97 (after the files dict is built), before `missing_files`:

```python
    # Subprojects only get harness config + yamllint — not CLAUDE.md, Makefile, pre-commit
    git_root = config.get("git_root")
    is_subproject = git_root is not None and project_dir.resolve() != git_root.resolve()
    if is_subproject:
        subproject_files = {".agent-harness.yml", ".yamllint.yml"}
        files = {k: v for k, v in files.items() if k in subproject_files}
```

- [ ] **Step 2: Run full test suite to verify no regressions**

Run: `uv run pytest tests/ -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add src/agent_harness/init/scaffold.py
git commit -m "fix: init only scaffolds harness config for monorepo subprojects"
```

---

### Task 12: Init CLAUDE.md recommendation wording

**Files:**
- Modify: `src/agent_harness/presets/universal/claudemd_setup.py`

- [ ] **Step 1: Update the recommendation message**

In `src/agent_harness/presets/universal/claudemd_setup.py`, change line 47-49:

Old:
```python
                    "mentions lint but not `make check` — "
                    "run the agent-harness skill to audit workflow instructions"
```

New:
```python
                    "CLAUDE.md should mention `make check` as the full quality gate "
                    "(lint + test + security-audit)"
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/ -v`
Expected: All PASS (no tests assert on the exact message text)

- [ ] **Step 3: Commit**

```bash
git add src/agent_harness/presets/universal/claudemd_setup.py
git commit -m "fix: improve CLAUDE.md init recommendation wording"
```

---

### Task 13: Skill doc updates

**Files:**
- Modify: `skills/agent-harness/SKILL.md`

- [ ] **Step 1: Add redundant tooling guidance to SKILL.md**

In the Step 1.5 audit section (around line 27-48), add a new item to the "What to look for" list:

```markdown
7. **Redundant security tooling.** If a Makefile target runs `pip-audit`, `npm audit`, or `gitleaks` directly, replace with `agent-harness security-audit` which combines dependency scanning + secret detection in one command.
```

- [ ] **Step 2: Add gitignore cleanup guidance**

After the existing Step 2 (Apply fixes), add to Step 2.5 or create a new note:

In the audit CLAUDE.md section or as a new Step 2.7, add:

```markdown
### Step 2.7: Review .gitignore

After `init --apply` appends missing patterns, review the full `.gitignore`:
- Remove patterns for stacks no longer in the project (e.g., Dagster patterns in a project that no longer uses Dagster)
- Consolidate duplicates that init couldn't detect (near-matches, overlapping globs)
- Reorganize into logical category sections if the file has grown disorganized

This is a judgment call — init does the safe mechanical work (grouped append), the agent does the contextual cleanup.
```

- [ ] **Step 3: Commit**

```bash
git add skills/agent-harness/SKILL.md
git commit -m "docs: add redundant tooling + gitignore cleanup guidance to skill"
```

---

### Task 14: Remove dead code and run full quality gate

**Files:**
- Modify: `src/agent_harness/workspace.py` (remove SKIP_DIRS export if no longer imported)
- Check: `src/agent_harness/detect.py` (verify no SKIP_DIRS import)

- [ ] **Step 1: Check for remaining SKIP_DIRS references**

Run: `grep -r "SKIP_DIRS" src/ tests/`

If `SKIP_DIRS` is only used in `git_files.py` fallback (imported from workspace), and workspace no longer defines it, clean up. The fallback in `git_files.py` defines its own `_skip` set, so `SKIP_DIRS` is fully dead.

- [ ] **Step 2: Remove `SKIP_DIRS` from workspace.py if still present**

It was already replaced in Task 2. Verify the old `_scan` function and `SKIP_DIRS` constant are gone.

- [ ] **Step 3: Run full quality gate**

```bash
make check
```

Expected: All lint, test, and security-audit pass.

- [ ] **Step 4: Fix any failures from `make check`**

Address any issues found by the quality gate.

- [ ] **Step 5: Commit any cleanup**

```bash
git add -A
git commit -m "chore: remove dead SKIP_DIRS, pass full quality gate"
```
