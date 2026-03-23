# v0.2: CLI Simplification + Monorepo Support

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify CLI to four clear commands (detect → init → lint → fix), add monorepo support via distributed dotfiles with automatic subproject discovery, scaffold Makefile with `make lint` target.

**Architecture:** Each project directory is a self-contained harness scope with its own `.agent-harness.yml`. `detect` scans the tree for subprojects. `lint --all` runs lint in every discovered scope in parallel. `init` scaffolds configs + Makefile. `audit` is removed — its responsibilities split between `detect` (discovery) and `init` (gap reporting).

**Key decisions from design session:**
- Distributed dotfiles, not root index file (avoids merge conflicts, each project self-contained)
- Dotfiles ARE the index — `lint --all` finds them by scanning
- Tools run per-project directory (ruff in backend/, biome in frontend/) because deps are local
- `detect` always scans subdirectories, no flag needed
- Makefile scaffolded by `init` — `make lint` is the universal entry point
- Parallel execution for monorepos

---

## CLI Surface (v0.2)

```
$ agent-harness --help
Commands:
  detect   Show detected stacks and subprojects
  init     Scaffold configs and Makefile for detected stacks
  lint     Run all harness checks
  fix      Auto-fix then lint
```

### detect

Always scans. Shows root + subprojects. Flags unharnessed projects.

```
$ agent-harness detect
.              python, docker
backend/       python (no .agent-harness.yml)
frontend/      javascript (no .agent-harness.yml)
services/auth/ python (no .agent-harness.yml)
```

### init

Creates `.agent-harness.yml`, `Makefile`, tool configs. Shows what was detected and what each tool does. `--yes` skips confirmation.

```
$ agent-harness init
  Detected stacks: python, docker

  python:
    ruff     — linting + formatting
    ty       — type checking
    conftest — pyproject.toml config enforcement

  docker:
    hadolint  — Dockerfile best practices
    conftest  — compose healthchecks, image pinning, ports, volumes
    yamllint  — YAML validation

  Proceed? [Y/n] y

  CREATE  .agent-harness.yml
  CREATE  Makefile
  CREATE  .yamllint.yml

  Harness initialized. Run: make lint
```

### lint

Runs all checks for current directory. `--all` discovers subprojects and runs each in parallel.

```
$ agent-harness lint
  8 passed, 0 failed (476ms)

$ agent-harness lint --all
  === . ===
    4 passed, 0 failed
  === backend/ ===
    4 passed, 0 failed
  === frontend/ ===
    3 passed, 0 failed

  11 passed, 0 failed (523ms)
```

### fix

Auto-fix then lint. `--all` for monorepos.

```
$ agent-harness fix --all
  Fixing...
    .: ruff formatted, ruff fixed
    frontend/: biome fixed
  Linting...
    11 passed, 0 failed
```

---

## Breaking Changes from v0.1

| v0.1 | v0.2 | Migration |
|------|------|-----------|
| `audit` command | Removed | `detect` for discovery, `init` for setup |
| No Makefile scaffolding | `init` creates Makefile | Re-run `init` |
| `lint` only current dir | `lint --all` for monorepos | Add `--all` if needed |

---

## File Structure

### Modified
- `src/agent_harness/cli.py` — remove `audit`, add `--all` to lint/fix, add `--yes` to init, update detect output format
- `src/agent_harness/detect.py` — add subproject scanning (walk subdirs for stack indicators)
- `src/agent_harness/lint.py` — add `run_lint_all()` that discovers `.agent-harness.yml` files and runs lint per scope in parallel
- `src/agent_harness/fix.py` — add `run_fix_all()` parallel equivalent
- `src/agent_harness/init/scaffold.py` — scaffold Makefile, add confirmation prompt, report detected stacks with descriptions

### Created
- `src/agent_harness/workspace.py` — discover subproject roots by scanning for `.agent-harness.yml` files

### Deleted
- `src/agent_harness/audit.py` — responsibilities absorbed by detect + init

### Tests
- Modify: `tests/test_cli.py` — update for new command surface
- Modify: `tests/test_detect.py` — add subproject scanning tests
- Create: `tests/test_workspace.py` — test root discovery
- Modify: `tests/test_init.py` — Makefile scaffolding, confirmation prompt
- Delete: `tests/test_audit.py` (if exists)

---

## Tasks

### Task 1: Workspace discovery module

Create `src/agent_harness/workspace.py` — scans for `.agent-harness.yml` files in subdirectories.

**Files:**
- Create: `src/agent_harness/workspace.py`
- Create: `tests/test_workspace.py`

- [ ] **Step 1: Write failing tests**

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
    (tmp_path / ".agent-harness.yml").write_text("stacks: [python]")
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / ".agent-harness.yml").write_text("stacks: [python]")
    roots = discover_roots(tmp_path)
    assert venv not in roots


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

- [ ] **Step 2: Implement workspace.py**

```python
# src/agent_harness/workspace.py
"""
Workspace discovery.

Finds all project roots (directories with .agent-harness.yml) in a repo tree.
Used by `lint --all` and `fix --all` to run checks across monorepo subprojects.
"""
from __future__ import annotations

from pathlib import Path

# Directories to never scan into
SKIP_DIRS = {
    ".venv", "venv", "node_modules", ".git", "dist", "build",
    "__pycache__", ".astro", ".next", ".nuxt", ".worktrees",
    "_archive",
}


def discover_roots(project_dir: Path, max_depth: int = 4) -> list[Path]:
    """Find directories containing .agent-harness.yml, up to max_depth."""
    roots = []
    _scan(project_dir, roots, depth=0, max_depth=max_depth)
    return sorted(roots)


def _scan(directory: Path, roots: list[Path], depth: int, max_depth: int) -> None:
    if depth > max_depth:
        return
    if directory.name in SKIP_DIRS:
        return
    if (directory / ".agent-harness.yml").exists():
        roots.append(directory)
    for child in sorted(directory.iterdir()):
        if child.is_dir() and not child.name.startswith(".") or child.name in {".agent-harness.yml"}:
            _scan(child, roots, depth + 1, max_depth)
```

Note: the `_scan` logic needs care — we skip dot-dirs except we still need to check the root itself. Implementer should refine.

- [ ] **Step 3: Run tests, commit**

---

### Task 2: Update detect to scan subprojects

Modify `detect` to show root + subproject stacks with status.

**Files:**
- Modify: `src/agent_harness/detect.py`
- Modify: `src/agent_harness/cli.py` (detect command output)
- Modify: `tests/test_detect.py`

- [ ] **Step 1: Write failing test**

```python
def test_detect_subprojects(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "package.json").write_text('{"name":"y"}')
    from agent_harness.detect import detect_all
    results = detect_all(tmp_path)
    assert results[tmp_path] == {"python"}
    assert results[backend] == {"javascript"}
```

- [ ] **Step 2: Add `detect_all()` to detect.py**

Scans root + subdirectories for stack indicators. Returns `dict[Path, set[str]]`. Uses same SKIP_DIRS as workspace module.

- [ ] **Step 3: Update CLI detect command**

Format output as:
```
.              python, docker
backend/       javascript (no .agent-harness.yml)
```

- [ ] **Step 4: Run tests, commit**

---

### Task 3: Scaffold Makefile in init

`agent-harness init` creates a Makefile with `lint`, `fix`, `test` targets.

**Files:**
- Modify: `src/agent_harness/init/scaffold.py`
- Modify: `src/agent_harness/init/templates.py`
- Modify: `tests/test_init.py`

- [ ] **Step 1: Add Makefile template**

```python
# In templates.py
MAKEFILE = """\
.PHONY: lint fix test

lint:
\tagent-harness lint

fix:
\tagent-harness fix

test:
\t{test_command}
"""

MAKEFILE_MONOREPO = """\
.PHONY: lint fix

lint:
\tagent-harness lint --all

fix:
\tagent-harness fix --all
"""
```

- [ ] **Step 2: Update scaffold to create Makefile**

Add Makefile to the files dict. Detect if monorepo (subprojects exist) and use appropriate template. Test command depends on stack (pytest for python, npm test for JS).

- [ ] **Step 3: Add confirmation prompt**

```python
def scaffold_project(project_dir: Path, yes: bool = False) -> list[str]:
    # ... detect, build file list ...
    if not yes:
        click.echo("Proceed? [Y/n]")
        if input().strip().lower() == 'n':
            return ["Cancelled"]
    # ... create files ...
```

- [ ] **Step 4: Tests, commit**

---

### Task 4: lint --all (parallel monorepo)

`agent-harness lint --all` discovers subprojects and runs lint in each.

**Files:**
- Modify: `src/agent_harness/lint.py`
- Modify: `src/agent_harness/cli.py`
- Create: `tests/test_lint_all.py`

- [ ] **Step 1: Write failing test**

```python
def test_lint_all_discovers_subprojects(tmp_path):
    # Create root + subproject with .agent-harness.yml
    # Run run_lint_all(tmp_path)
    # Assert results from both scopes
```

- [ ] **Step 2: Implement run_lint_all**

```python
from concurrent.futures import ProcessPoolExecutor
from agent_harness.workspace import discover_roots

def run_lint_all(project_dir: Path) -> dict[Path, list[CheckResult]]:
    roots = discover_roots(project_dir)
    results = {}
    with ProcessPoolExecutor() as pool:
        futures = {pool.submit(run_lint, root): root for root in roots}
        for future in futures:
            root = futures[future]
            results[root] = future.result()
    return results
```

- [ ] **Step 3: Update CLI lint command with --all flag**

- [ ] **Step 4: Tests, commit**

---

### Task 5: fix --all + remove audit command

Add `--all` to fix, remove audit command entirely.

**Files:**
- Modify: `src/agent_harness/fix.py`
- Modify: `src/agent_harness/cli.py` (remove audit, add --all to fix)
- Delete: `src/agent_harness/audit.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add run_fix_all (same pattern as lint)**

- [ ] **Step 2: Remove audit command from CLI**

- [ ] **Step 3: Update init to absorb useful audit checks** (tool installation status, gitignore completeness — report during init)

- [ ] **Step 4: Tests, commit**

---

### Task 6: Integration test on real projects

- [ ] Run on agent-harness repo itself
- [ ] Run on iorlas.github.io (blog)
- [ ] Run on proxy-hub (monorepo case)
- [ ] Verify `detect` shows subprojects
- [ ] Verify `lint --all` works on monorepo
- [ ] Verify `init` scaffolds Makefile
- [ ] Update README, PLANS.md
- [ ] Commit, push
