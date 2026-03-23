# JavaScript Stack + Universal Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add JavaScript/TypeScript stack support (Biome, framework type checkers, package.json Rego policies) and fix universal issues exposed by running agent-harness on a real JS project (file exclusions, stack-specific gitignore, JSONC skipping, extension-aware file length).

**Architecture:** Two phases — Phase A fixes universal infrastructure that all stacks depend on (exclusions, gitignore split, JSONC, file length generalization). Phase B adds the JS stack module following existing patterns (detect.py, check files with WHAT/WHY docstrings, Rego policies, templates). Framework-specific type checkers (astro check, tsc, next lint) are selected via detection, not config.

**Tech Stack:** Python 3.12+, Click CLI, conftest/Rego, Biome, yamllint, pytest

**Existing patterns to follow:**
- Each check = one file with WHAT/WHY/WITHOUT IT/FIX/REQUIRES docstring
- Detection = file presence indicators in per-stack `detect.py`
- Tool fallback = `shutil.which()` then `npx`/`uv run`
- Tests = `tmp_path` fixtures, mock subprocesses via `monkeypatch`
- Rego = `deny contains msg if {}` + `_test.rego` sibling

**Reference: blog project that exposed issues** — `~/Workspaces/iorlas.github.io` (Astro 6, TypeScript, no linting, no tests, `.gitignore` missing Python entries flagged incorrectly)

---

## File Structure

### Phase A: Universal fixes

```
src/agent_harness/
  config.py                              # MODIFY: add exclude list + JavaScriptConfig
  exclusions.py                          # CREATE: file exclusion logic
  stacks/universal/
    conftest_json_check.py               # MODIFY: skip known JSONC files
    conftest_gitignore_check.py          # MODIFY: pass detected stacks to conftest via --data
    file_length_check.py                 # MOVE from stacks/python/ → universal, make extension-aware
  stacks/python/
    file_length_check.py                 # DELETE (moved to universal)

policies/gitignore/
  secrets.rego                           # MODIFY: split into universal + stack-conditional rules

tests/
  test_exclusions.py                     # CREATE
  stacks/universal/
    test_conftest_json_check.py          # MODIFY: add JSONC skip test
    test_conftest_gitignore_check.py     # MODIFY: add stack-conditional tests
    test_file_length_check.py            # CREATE (moved from python/)
  stacks/python/
    test_file_length_check.py            # DELETE (moved to universal)
```

### Phase B: JavaScript stack

```
src/agent_harness/stacks/javascript/
  __init__.py                            # CREATE
  detect.py                              # CREATE: package.json, tsconfig.json indicators
  biome_check.py                         # CREATE: biome check + biome format
  type_check.py                          # CREATE: framework-aware (astro check > tsc --noEmit)
  conftest_package_check.py              # CREATE: Rego policies on package.json
  templates.py                           # CREATE: biome.json, tsconfig strict template

policies/javascript/
  package.rego                           # CREATE: engines, type:module, no * versions
  package_test.rego                      # CREATE

tests/
  stacks/javascript/
    __init__.py                          # CREATE
    test_detect.py                       # CREATE
    test_biome_check.py                  # CREATE
    test_type_check.py                   # CREATE
    test_conftest_package_check.py       # CREATE

src/agent_harness/
  detect.py                              # MODIFY: add javascript detection
  lint.py                                # MODIFY: add JS checks + exclusion filtering
  fix.py                                 # MODIFY: add biome fix
  audit.py                               # MODIFY: add JS tool checks
  init/scaffold.py                       # MODIFY: JS-aware scaffolding
  init/templates.py                      # MODIFY: add JS config templates
```

---

## Phase A: Universal Fixes

### Task 1: File exclusion system

Add `exclude` list to `.agent-harness.yml` config + built-in defaults. All checks that enumerate files (`git ls-files`) must respect exclusions.

**Files:**
- Modify: `src/agent_harness/config.py`
- Create: `src/agent_harness/exclusions.py`
- Modify: `tests/test_config.py`
- Create: `tests/test_exclusions.py`

**Built-in default exclusions** (always applied, before config):
```
*-lock.*
*.lock
package-lock.json
node_modules/
dist/
.venv/
__pycache__/
.astro/
.next/
_archive/
```

- [ ] **Step 1: Write failing test for exclusions module**

```python
# tests/test_exclusions.py
from agent_harness.exclusions import get_excluded_patterns, is_excluded


def test_default_exclusions_include_lock_files():
    patterns = get_excluded_patterns([])
    assert "*.lock" in patterns
    assert "package-lock.json" in patterns


def test_config_exclusions_extend_defaults():
    patterns = get_excluded_patterns(["vendor/", "generated/"])
    assert "*.lock" in patterns
    assert "vendor/" in patterns


def test_is_excluded_matches_lock_file():
    patterns = get_excluded_patterns([])
    assert is_excluded("pnpm-lock.yaml", patterns)
    assert is_excluded("package-lock.json", patterns)
    assert not is_excluded("src/main.py", patterns)


def test_is_excluded_matches_directory_prefix():
    patterns = get_excluded_patterns(["_archive/"])
    assert is_excluded("_archive/old/tsconfig.json", patterns)
    assert not is_excluded("src/archive.py", patterns)


def test_is_excluded_matches_glob():
    patterns = get_excluded_patterns([])
    assert is_excluded("poetry.lock", patterns)
    assert is_excluded("yarn.lock", patterns)
    assert is_excluded("Gemfile.lock", patterns)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/test_exclusions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_harness.exclusions'`

- [ ] **Step 3: Implement exclusions module**

```python
# src/agent_harness/exclusions.py
"""
File exclusion system.

WHAT: Provides default and configurable file exclusion patterns for all checks.

WHY: Without exclusions, agent-harness scans lock files, build output, archives,
and vendored code. This wastes time (yamllint on pnpm-lock.yaml: 1.7s) and
produces false positives (JSONC parse failures on tsconfig.json in _archive/).

WITHOUT IT: 2.5s lint runs that should be 200ms, false positives on generated
files, agents fixing issues in files they shouldn't touch.

FIX: Add patterns to `exclude:` in .agent-harness.yml.
"""
from __future__ import annotations

import fnmatch

DEFAULT_EXCLUSIONS = [
    # Lock files
    "*.lock",
    "*-lock.*",
    "package-lock.json",
    # Build output
    "dist/",
    ".astro/",
    ".next/",
    ".nuxt/",
    # Dependencies
    "node_modules/",
    ".venv/",
    # Caches
    "__pycache__/",
    ".pytest_cache/",
    ".ruff_cache/",
    # Archives
    "_archive/",
]


def get_excluded_patterns(config_exclude: list[str]) -> list[str]:
    """Merge default exclusions with config-provided ones."""
    return DEFAULT_EXCLUSIONS + config_exclude


def is_excluded(filepath: str, patterns: list[str]) -> bool:
    """Check if a filepath matches any exclusion pattern."""
    for pattern in patterns:
        # Directory prefix match: "dist/" matches "dist/foo/bar.js"
        if pattern.endswith("/") and filepath.startswith(pattern):
            return True
        # Also match if any path segment matches directory pattern
        if pattern.endswith("/"):
            dir_name = pattern.rstrip("/")
            if f"/{dir_name}/" in f"/{filepath}" or filepath.startswith(f"{dir_name}/"):
                return True
        # Glob match: "*.lock" matches "poetry.lock"
        if fnmatch.fnmatch(filepath, pattern):
            return True
        # Also match basename: "*-lock.*" matches "path/to/pnpm-lock.yaml"
        if fnmatch.fnmatch(filepath.split("/")[-1], pattern):
            return True
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/test_exclusions.py -v`
Expected: PASS

- [ ] **Step 5: Add `exclude` to config**

Modify `src/agent_harness/config.py` — add `exclude: list[str]` to `HarnessConfig`:

```python
@dataclass
class HarnessConfig:
    stacks: set[str] = field(default_factory=set)
    exclude: list[str] = field(default_factory=list)
    python: PythonConfig = field(default_factory=PythonConfig)
    docker: DockerConfig = field(default_factory=DockerConfig)
```

In `load_config()`, add after stacks parsing:
```python
if "exclude" in raw:
    config.exclude = list(raw["exclude"])
```

- [ ] **Step 6: Add config test for exclude**

Add to `tests/test_config.py`:
```python
def test_load_config_with_exclude(tmp_path):
    (tmp_path / ".agent-harness.yml").write_text(
        "stacks: [python]\nexclude:\n  - _archive/\n  - vendor/\n"
    )
    config = load_config(tmp_path)
    assert "_archive/" in config.exclude
    assert "vendor/" in config.exclude


def test_load_config_exclude_defaults_empty(tmp_path):
    config = load_config(tmp_path)
    assert config.exclude == []
```

- [ ] **Step 7: Run all tests**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/test_config.py tests/test_exclusions.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/agent_harness/exclusions.py tests/test_exclusions.py src/agent_harness/config.py tests/test_config.py
git commit -m "feat: add file exclusion system with defaults for lock files, build output, archives"
```

---

### Task 2: Wire exclusions into yamllint and conftest-json checks

These two checks enumerate files via `git ls-files` and need to filter through exclusions.

**Files:**
- Modify: `src/agent_harness/stacks/universal/yamllint_check.py`
- Modify: `src/agent_harness/stacks/universal/conftest_json_check.py`
- Modify: `src/agent_harness/lint.py` (pass config to checks)
- Modify: `tests/stacks/universal/test_yamllint_check.py`
- Modify: `tests/stacks/universal/test_conftest_json_check.py`

- [ ] **Step 1: Write failing test — yamllint skips excluded files**

Add to `tests/stacks/universal/test_yamllint_check.py`:
```python
def test_yamllint_skips_lock_files(tmp_path, monkeypatch):
    """Lock files should be excluded even if git-tracked."""
    import subprocess

    # Simulate git ls-files returning a lock file
    def mock_run(cmd, **kwargs):
        if "ls-files" in cmd:
            result = subprocess.CompletedProcess(cmd, 0, stdout="pnpm-lock.yaml\n", stderr="")
            return result
        return subprocess.run(cmd, **kwargs)

    monkeypatch.setattr("agent_harness.stacks.universal.yamllint_check.subprocess.run", mock_run)

    result = run_yamllint(tmp_path, exclude_patterns=["*-lock.*", "*.lock"])
    assert result.passed
    assert "skipping" in result.output.lower() or "No YAML" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/stacks/universal/test_yamllint_check.py -v`
Expected: FAIL — `run_yamllint()` doesn't accept `exclude_patterns`

- [ ] **Step 3: Update yamllint_check.py to accept and apply exclusions**

Modify `run_yamllint` signature and body:
```python
from agent_harness.exclusions import is_excluded

def run_yamllint(project_dir: Path, exclude_patterns: list[str] | None = None) -> CheckResult:
    result = subprocess.run(
        ["git", "ls-files", "*.yml", "*.yaml"],
        capture_output=True, text=True, cwd=str(project_dir)
    )
    yaml_files = [f for f in result.stdout.strip().splitlines() if f]

    # Filter exclusions
    if exclude_patterns:
        yaml_files = [f for f in yaml_files if not is_excluded(f, exclude_patterns)]

    if not yaml_files:
        return CheckResult(name="yamllint", passed=True, output="No YAML files (after exclusions), skipping")
    # ... rest unchanged
```

- [ ] **Step 4: Write failing test — conftest-json skips JSONC files**

Add to `tests/stacks/universal/test_conftest_json_check.py`:
```python
def test_conftest_json_skips_jsonc_files(tmp_path, monkeypatch):
    """tsconfig.json and jsconfig.json are JSONC — skip them."""
    import subprocess

    def mock_run(cmd, **kwargs):
        if "ls-files" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="tsconfig.json\npackage.json\n", stderr="")
        # Only package.json should be parsed
        if "conftest" in cmd and "tsconfig.json" in str(cmd):
            raise AssertionError("Should not parse tsconfig.json")
        return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

    monkeypatch.setattr("agent_harness.stacks.universal.conftest_json_check.subprocess.run", mock_run)

    result = run_conftest_json(tmp_path, exclude_patterns=[])
    # Should not fail on tsconfig.json
    assert result.passed
```

- [ ] **Step 5: Update conftest_json_check.py — skip JSONC + apply exclusions**

```python
from agent_harness.exclusions import is_excluded

# Files known to use JSONC (comments, trailing commas) — conftest can't parse them
JSONC_FILES = {"tsconfig.json", "jsconfig.json"}
JSONC_DIRS = {".vscode"}

def _is_jsonc(filepath: str) -> bool:
    """Check if a JSON file is actually JSONC."""
    basename = filepath.split("/")[-1]
    if basename in JSONC_FILES:
        return True
    parts = filepath.split("/")
    return any(d in JSONC_DIRS for d in parts[:-1])

def run_conftest_json(project_dir: Path, exclude_patterns: list[str] | None = None) -> CheckResult:
    # ... existing git ls-files ...
    json_files = [f for f in result.stdout.strip().splitlines() if f]

    # Filter JSONC and excluded files
    json_files = [f for f in json_files if not _is_jsonc(f)]
    if exclude_patterns:
        json_files = [f for f in json_files if not is_excluded(f, exclude_patterns)]

    # ... rest unchanged
```

- [ ] **Step 6: Update lint.py to pass exclusions from config**

```python
from agent_harness.exclusions import get_excluded_patterns

def run_lint(project_dir: Path) -> list[CheckResult]:
    config = load_config(project_dir)
    exclude = get_excluded_patterns(config.exclude)
    results: list[CheckResult] = []

    # Universal checks
    results.append(run_conftest_gitignore(project_dir))
    results.append(run_conftest_json(project_dir, exclude_patterns=exclude))
    results.append(run_yamllint(project_dir, exclude_patterns=exclude))

    # Python checks
    if "python" in config.stacks:
        results.extend(run_ruff(project_dir))
        results.append(run_ty(project_dir))
        results.append(run_conftest_python(project_dir))
        results.append(run_file_length(project_dir, config.python.max_file_lines))

    # Docker checks (unchanged)
    if "docker" in config.stacks:
        results.append(run_conftest_dockerfile(project_dir))
        results.append(run_conftest_compose(project_dir, config.docker.own_image_prefix))
        results.append(run_hadolint(project_dir))

    return results
```

- [ ] **Step 7: Run all tests**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
git add src/agent_harness/stacks/universal/yamllint_check.py src/agent_harness/stacks/universal/conftest_json_check.py src/agent_harness/lint.py tests/stacks/universal/
git commit -m "feat: wire exclusions into yamllint and conftest-json, skip JSONC files"
```

---

### Task 3: Stack-specific gitignore policies

Split the monolithic gitignore Rego into universal + per-stack. The conftest check passes detected stacks as data so Rego can conditionally check entries.

**Files:**
- Modify: `policies/gitignore/secrets.rego`
- Modify: `policies/gitignore/secrets_test.rego`
- Modify: `src/agent_harness/stacks/universal/conftest_gitignore_check.py`
- Modify: `src/agent_harness/lint.py`
- Modify: `tests/stacks/universal/test_conftest_gitignore_check.py`

**Important:** conftest supports `--data <file>` to inject external data into Rego evaluation. Verify with `conftest test --help | grep data`. The data file is JSON and becomes available as `data.*` in Rego.

- [ ] **Step 1: Verify conftest --data flag works**

```bash
cd ~/Workspaces/ai-harness
echo '{"stacks": ["python"]}' > /tmp/test_data.json
conftest test --help | grep -A2 "data"
```
Expected: Shows `--data` flag documentation

- [ ] **Step 2: Redesign the Rego policy with stack-conditional rules**

Replace `policies/gitignore/secrets.rego`:
```rego
package gitignore.secrets

# GITIGNORE — secrets and artifacts must be excluded, per detected stack
#
# WHAT: Ensures .env is always gitignored, plus stack-specific entries
# (.venv/__pycache__ for Python, node_modules/dist for JS).
#
# WHY: Agents create .env files with real secrets. Stack-specific artifacts
# (.venv, node_modules) bloat repos. Without stack awareness, Python entries
# get flagged on JS projects (false positives) and JS entries get missed on
# JS projects (false negatives).
#
# WITHOUT IT: Secrets in git history, false positive noise on wrong stacks,
# missing entries for detected stacks.
#
# FIX: Add the reported entries to .gitignore.
#
# Input: array of [{Kind, Value, Original}] entries
# Data: {stacks: ["python", "javascript", ...]} passed via --data

import rego.v1

# ── Universal: .env must always be gitignored ──

deny contains msg if {
	not _pattern_present(".env")
	msg := ".gitignore: '.env' is not ignored — agents create .env with real secrets"
}

# ── Python stack ──

deny contains msg if {
	"python" in data.stacks
	not _pattern_present(".venv")
	msg := ".gitignore: '.venv' is not ignored — Python virtual environments bloat the repo"
}

deny contains msg if {
	"python" in data.stacks
	not _pattern_present("__pycache__")
	msg := ".gitignore: '__pycache__' is not ignored — compiled bytecode should not be tracked"
}

# ── JavaScript stack ──

deny contains msg if {
	"javascript" in data.stacks
	not _pattern_present("node_modules")
	msg := ".gitignore: 'node_modules' is not ignored — JS dependencies must not be committed"
}

deny contains msg if {
	"javascript" in data.stacks
	not _pattern_present("dist")
	msg := ".gitignore: 'dist' is not ignored — build output should not be tracked"
}

# ── Helper ──

_pattern_present(pattern) if {
	some entry in input
	entry.Kind == "Path"
	contains(entry.Value, pattern)
}
```

- [ ] **Step 3: Update the Rego test**

Replace `policies/gitignore/secrets_test.rego`:
```rego
package gitignore.secrets_test

import data.gitignore.secrets
import rego.v1

# Helper: minimal .gitignore with all required entries
mock_complete_input := [
	{"Kind": "Path", "Value": ".env", "Original": ".env"},
	{"Kind": "Path", "Value": ".venv/", "Original": ".venv/"},
	{"Kind": "Path", "Value": "__pycache__/", "Original": "__pycache__/"},
	{"Kind": "Path", "Value": "node_modules/", "Original": "node_modules/"},
	{"Kind": "Path", "Value": "dist/", "Original": "dist/"},
]

# Universal: .env always required
test_missing_env if {
	count(secrets.deny) > 0 with input as []
		with data.stacks as []
}

test_env_present if {
	count(secrets.deny) == 0 with input as mock_complete_input
		with data.stacks as ["python", "javascript"]
}

# Python: .venv required only when python detected
test_venv_required_for_python if {
	count(secrets.deny) > 0 with input as [{"Kind": "Path", "Value": ".env", "Original": ".env"}]
		with data.stacks as ["python"]
}

test_venv_not_required_without_python if {
	denials := secrets.deny with input as [{"Kind": "Path", "Value": ".env", "Original": ".env"}]
		with data.stacks as ["javascript"]
	not _contains_venv(denials)
}

_contains_venv(denials) if {
	some msg in denials
	contains(msg, ".venv")
}

# JavaScript: node_modules required only when javascript detected
test_node_modules_required_for_js if {
	count(secrets.deny) > 0 with input as [{"Kind": "Path", "Value": ".env", "Original": ".env"}]
		with data.stacks as ["javascript"]
}

test_node_modules_not_required_without_js if {
	denials := secrets.deny with input as [
		{"Kind": "Path", "Value": ".env", "Original": ".env"},
		{"Kind": "Path", "Value": ".venv/", "Original": ".venv/"},
		{"Kind": "Path", "Value": "__pycache__/", "Original": "__pycache__/"},
	]
		with data.stacks as ["python"]
	not _contains_node_modules(denials)
}

_contains_node_modules(denials) if {
	some msg in denials
	contains(msg, "node_modules")
}
```

- [ ] **Step 4: Run Rego tests**

Run: `cd ~/Workspaces/ai-harness && conftest verify -p policies/gitignore/ --no-color`
Expected: ALL PASS

- [ ] **Step 5: Update conftest_gitignore_check.py to pass stacks as data**

Modify `src/agent_harness/stacks/universal/conftest_gitignore_check.py`:

```python
import json
import tempfile

def run_conftest_gitignore(project_dir: Path, stacks: set[str] | None = None) -> CheckResult:
    """Run conftest on .gitignore with stack-conditional policies."""
    target = project_dir / ".gitignore"
    if not target.exists():
        return CheckResult(
            name="conftest-gitignore",
            passed=True,
            output="Skipping conftest-gitignore: .gitignore not found",
        )
    policy_path = POLICIES_DIR / "gitignore"

    # Write stacks data to temp file for conftest --data
    stacks_list = sorted(stacks) if stacks else []
    data_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump({"stacks": stacks_list}, data_file)
    data_file.close()

    cmd = [
        "conftest", "test", str(target),
        "--policy", str(policy_path),
        "--no-color", "--all-namespaces",
        "--data", data_file.name,
    ]
    return run_check("conftest-gitignore", cmd, cwd=str(project_dir))
```

- [ ] **Step 6: Update lint.py to pass stacks to gitignore check**

```python
results.append(run_conftest_gitignore(project_dir, stacks=config.stacks))
```

- [ ] **Step 7: Write Python test for stack-conditional gitignore**

Add to `tests/stacks/universal/test_conftest_gitignore_check.py`:
```python
from agent_harness.stacks.universal.conftest_gitignore_check import run_conftest_gitignore
import subprocess


def _init_git(tmp_path):
    """Initialize a git repo so conftest can run."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)


def test_gitignore_js_project_no_python_false_positives(tmp_path):
    """JS project should not be flagged for missing .venv or __pycache__."""
    _init_git(tmp_path)
    (tmp_path / ".gitignore").write_text(".env\nnode_modules/\ndist/\n")
    result = run_conftest_gitignore(tmp_path, stacks={"javascript"})
    assert result.passed, f"Should pass for JS project: {result.error or result.output}"


def test_gitignore_python_project_flags_venv(tmp_path):
    """Python project missing .venv should fail."""
    _init_git(tmp_path)
    (tmp_path / ".gitignore").write_text(".env\n")
    result = run_conftest_gitignore(tmp_path, stacks={"python"})
    assert not result.passed
    assert ".venv" in (result.error or result.output)
```

- [ ] **Step 8: Run all tests**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/ -v && conftest verify -p policies/ --no-color`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add policies/gitignore/ src/agent_harness/stacks/universal/conftest_gitignore_check.py src/agent_harness/lint.py tests/stacks/universal/test_conftest_gitignore_check.py
git commit -m "feat: stack-conditional gitignore policies — no more Python false positives on JS projects"
```

---

### Task 4: Extension-aware file length check (move to universal)

Move `file_length_check.py` from `stacks/python/` to `stacks/universal/`. Make it extension-aware with configurable thresholds per extension.

**Files:**
- Move: `src/agent_harness/stacks/python/file_length_check.py` → `src/agent_harness/stacks/universal/file_length_check.py`
- Delete: `tests/stacks/python/test_file_length_check.py` (if exists)
- Create: `tests/stacks/universal/test_file_length_check.py`
- Modify: `src/agent_harness/lint.py`

**Default thresholds:**
```python
DEFAULT_MAX_LINES = {
    ".py": 500,
    ".ts": 500,
    ".tsx": 500,
    ".js": 500,
    ".jsx": 500,
    ".astro": 800,
    ".vue": 800,
    ".svelte": 800,
}
```

- [ ] **Step 1: Write failing test for extension-aware file length**

```python
# tests/stacks/universal/test_file_length_check.py
import subprocess
from agent_harness.stacks.universal.file_length_check import run_file_length


def _init_git(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)


def test_py_file_over_500_fails(tmp_path):
    (tmp_path / "big.py").write_text("x = 1\n" * 501)
    _init_git(tmp_path)
    result = run_file_length(tmp_path)
    assert not result.passed
    assert "big.py" in (result.error or result.output)


def test_astro_file_under_800_passes(tmp_path):
    (tmp_path / "Page.astro").write_text("<div>hi</div>\n" * 750)
    _init_git(tmp_path)
    result = run_file_length(tmp_path)
    assert result.passed


def test_astro_file_over_800_fails(tmp_path):
    (tmp_path / "Page.astro").write_text("<div>hi</div>\n" * 801)
    _init_git(tmp_path)
    result = run_file_length(tmp_path)
    assert not result.passed


def test_custom_thresholds(tmp_path):
    (tmp_path / "small.py").write_text("x = 1\n" * 301)
    _init_git(tmp_path)
    result = run_file_length(tmp_path, max_lines_override={".py": 300})
    assert not result.passed


def test_excluded_files_skipped(tmp_path):
    (tmp_path / "big.py").write_text("x = 1\n" * 501)
    _init_git(tmp_path)
    result = run_file_length(tmp_path, exclude_patterns=["big.py"])
    assert result.passed


def test_unknown_extensions_skipped(tmp_path):
    (tmp_path / "data.csv").write_text("a,b\n" * 10000)
    _init_git(tmp_path)
    result = run_file_length(tmp_path)
    assert result.passed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/stacks/universal/test_file_length_check.py -v`
Expected: FAIL — import error (file doesn't exist at new location yet)

- [ ] **Step 3: Create universal file_length_check.py**

```python
# src/agent_harness/stacks/universal/file_length_check.py
"""
File length check.

WHAT: Ensures tracked source files don't exceed extension-specific line limits.

WHY: Agents generate monolith files that grow unboundedly. Long files are harder
to review, harder to test, and agents themselves lose context when editing 1000+
line files. Template-heavy files (.astro, .vue, .svelte) get a higher limit (800)
because HTML markup inflates line counts.

WITHOUT IT: 1000+ line files that no one reviews, circular dependencies from
everything-in-one-module, and agents that lose track of earlier code.

FIX: Split the file into focused modules. Extract classes, helpers, or
components into separate files.

REQUIRES: git (for file listing)
"""
from __future__ import annotations

from pathlib import Path
import subprocess

from agent_harness.runner import CheckResult
from agent_harness.exclusions import is_excluded

DEFAULT_MAX_LINES: dict[str, int] = {
    ".py": 500,
    ".ts": 500,
    ".tsx": 500,
    ".js": 500,
    ".jsx": 500,
    ".astro": 800,
    ".vue": 800,
    ".svelte": 800,
}


def run_file_length(
    project_dir: Path,
    max_lines_override: dict[str, int] | None = None,
    exclude_patterns: list[str] | None = None,
) -> CheckResult:
    """Check tracked source files against extension-specific line limits."""
    thresholds = {**DEFAULT_MAX_LINES, **(max_lines_override or {})}

    # Get all tracked files with relevant extensions
    extensions = list(thresholds.keys())
    git_patterns = [f"*{ext}" for ext in extensions]
    result = subprocess.run(
        ["git", "ls-files"] + git_patterns,
        capture_output=True, text=True, cwd=str(project_dir)
    )
    files = [f for f in result.stdout.strip().splitlines() if f]

    # Filter exclusions
    if exclude_patterns:
        files = [f for f in files if not is_excluded(f, exclude_patterns)]

    if not files:
        return CheckResult(name="file-length", passed=True, output="No tracked source files to check")

    errors = []
    for f in files:
        path = project_dir / f
        if not path.exists():
            continue
        ext = path.suffix
        max_lines = thresholds.get(ext)
        if max_lines is None:
            continue
        lines = len(path.read_text().splitlines())
        if lines > max_lines:
            errors.append(f"{f}: {lines} lines (max {max_lines} for {ext})")

    if errors:
        return CheckResult(name="file-length", passed=False, error="\n".join(errors))
    return CheckResult(
        name="file-length",
        passed=True,
        output=f"All {len(files)} files within extension-specific limits",
    )
```

- [ ] **Step 4: Run tests**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/stacks/universal/test_file_length_check.py -v`
Expected: PASS

- [ ] **Step 5: Delete old Python-specific file_length_check.py**

Remove `src/agent_harness/stacks/python/file_length_check.py` and its test (if exists at `tests/stacks/python/test_file_length_check.py`).

- [ ] **Step 6: Update lint.py — move file-length to universal, pass exclusions**

```python
from agent_harness.stacks.universal.file_length_check import run_file_length

def run_lint(project_dir: Path) -> list[CheckResult]:
    config = load_config(project_dir)
    exclude = get_excluded_patterns(config.exclude)
    results: list[CheckResult] = []

    # Universal checks
    results.append(run_conftest_gitignore(project_dir, stacks=config.stacks))
    results.append(run_conftest_json(project_dir, exclude_patterns=exclude))
    results.append(run_yamllint(project_dir, exclude_patterns=exclude))
    results.append(run_file_length(project_dir, exclude_patterns=exclude))

    # Python checks (file_length removed from here)
    if "python" in config.stacks:
        results.extend(run_ruff(project_dir))
        results.append(run_ty(project_dir))
        results.append(run_conftest_python(project_dir))

    # Docker checks
    if "docker" in config.stacks:
        results.append(run_conftest_dockerfile(project_dir))
        results.append(run_conftest_compose(project_dir, config.docker.own_image_prefix))
        results.append(run_hadolint(project_dir))

    return results
```

- [ ] **Step 7: Run all tests**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/ -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git rm src/agent_harness/stacks/python/file_length_check.py
git add src/agent_harness/stacks/universal/file_length_check.py tests/stacks/universal/test_file_length_check.py src/agent_harness/lint.py
git commit -m "feat: extension-aware file length check — .py/.ts 500, .astro/.vue 800, moved to universal"
```

---

## Phase B: JavaScript Stack

### Task 5: JavaScript stack detection

**Files:**
- Create: `src/agent_harness/stacks/javascript/__init__.py`
- Create: `src/agent_harness/stacks/javascript/detect.py`
- Modify: `src/agent_harness/detect.py`
- Create: `tests/stacks/javascript/__init__.py`
- Create: `tests/stacks/javascript/test_detect.py`
- Modify: `tests/test_detect.py`

- [ ] **Step 1: Write failing detection tests**

```python
# tests/stacks/javascript/test_detect.py
from agent_harness.stacks.javascript.detect import detect_javascript


def test_detect_package_json(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}')
    assert detect_javascript(tmp_path)


def test_detect_tsconfig(tmp_path):
    (tmp_path / "tsconfig.json").write_text('{}')
    assert detect_javascript(tmp_path)


def test_detect_none(tmp_path):
    assert not detect_javascript(tmp_path)


def test_detect_python_only(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    assert not detect_javascript(tmp_path)
```

Also add to `tests/test_detect.py`:
```python
def test_detect_javascript(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}')
    assert "javascript" in detect_stacks(tmp_path)


def test_detect_javascript_and_docker(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}')
    (tmp_path / "Dockerfile").write_text("FROM node:22")
    stacks = detect_stacks(tmp_path)
    assert "javascript" in stacks and "docker" in stacks
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/stacks/javascript/test_detect.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement detection**

```python
# src/agent_harness/stacks/javascript/__init__.py
# (empty)

# src/agent_harness/stacks/javascript/detect.py
"""Detect whether a project uses the JavaScript/TypeScript stack."""
from pathlib import Path

JS_INDICATORS = ["package.json", "tsconfig.json", "deno.json"]


def detect_javascript(project_dir: Path) -> bool:
    """Return True if the project contains JavaScript/TypeScript stack indicators."""
    return any((project_dir / f).exists() for f in JS_INDICATORS)
```

- [ ] **Step 4: Wire into detect.py orchestrator**

```python
from agent_harness.stacks.javascript.detect import detect_javascript

def detect_stacks(project_dir: Path) -> set[str]:
    stacks = set()
    if detect_python(project_dir):
        stacks.add("python")
    if detect_docker(project_dir):
        stacks.add("docker")
    if detect_javascript(project_dir):
        stacks.add("javascript")
    return stacks
```

- [ ] **Step 5: Run all tests**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/ -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/agent_harness/stacks/javascript/ tests/stacks/javascript/ src/agent_harness/detect.py tests/test_detect.py
git commit -m "feat: JavaScript/TypeScript stack detection"
```

---

### Task 6: Biome check (lint + format)

**Files:**
- Create: `src/agent_harness/stacks/javascript/biome_check.py`
- Create: `tests/stacks/javascript/test_biome_check.py`

- [ ] **Step 1: Write failing test**

```python
# tests/stacks/javascript/test_biome_check.py
from unittest.mock import patch, MagicMock
from agent_harness.stacks.javascript.biome_check import run_biome


def test_biome_returns_two_results(tmp_path):
    """Biome should run lint and format checks."""
    with patch("agent_harness.stacks.javascript.biome_check.shutil.which", return_value="/usr/bin/biome"):
        with patch("agent_harness.stacks.javascript.biome_check.run_check") as mock_run:
            mock_run.return_value = MagicMock(passed=True, output="", error="", duration_ms=10, name="biome")
            results = run_biome(tmp_path)
            assert len(results) == 2
            assert any("lint" in r.name for r in results)
            assert any("format" in r.name for r in results)


def test_biome_falls_back_to_npx(tmp_path):
    """When biome not in PATH, use npx."""
    with patch("agent_harness.stacks.javascript.biome_check.shutil.which", return_value=None):
        with patch("agent_harness.stacks.javascript.biome_check.run_check") as mock_run:
            mock_run.return_value = MagicMock(passed=True, output="", error="", duration_ms=10, name="biome")
            run_biome(tmp_path)
            calls = mock_run.call_args_list
            assert any("npx" in str(c) for c in calls)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/stacks/javascript/test_biome_check.py -v`
Expected: FAIL

- [ ] **Step 3: Implement biome_check.py**

```python
# src/agent_harness/stacks/javascript/biome_check.py
"""
Biome lint and format check.

WHAT: Runs biome lint and biome format --check on the project.

WHY: Biome is the ruff of JavaScript — a single Rust-based tool for linting and
formatting, ~20x faster than ESLint. Agents generate code with unused variables,
inconsistent formatting, implicit type coercion, and console.log left in
production code. Biome catches all of these in one pass.

WITHOUT IT: Style drift between agent iterations, unused variables accumulate,
console.log ships to production, formatting wars between agent and human edits.

FIX: Run `biome check --fix` to auto-fix, or `agent-harness fix`.

REQUIRES: biome (via PATH or npx fallback)
"""
from pathlib import Path
import shutil

from agent_harness.runner import run_check, CheckResult


def run_biome(project_dir: Path) -> list[CheckResult]:
    """Run biome lint and biome format --check. Returns list of results."""
    results = []
    if shutil.which("biome"):
        prefix = ["biome"]
    else:
        prefix = ["npx", "@biomejs/biome"]

    results.append(run_check(
        "biome:lint",
        prefix + ["lint", "."],
        cwd=str(project_dir),
    ))
    results.append(run_check(
        "biome:format",
        prefix + ["format", "--check", "."],
        cwd=str(project_dir),
    ))
    return results
```

- [ ] **Step 4: Run tests**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/stacks/javascript/test_biome_check.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent_harness/stacks/javascript/biome_check.py tests/stacks/javascript/test_biome_check.py
git commit -m "feat: Biome lint + format check for JavaScript stack"
```

---

### Task 7: Framework-aware type checking

Detect which framework is in use and pick the right type checker:
- Astro → `astro check`
- Next.js → `next lint` (includes tsc)
- Default → `tsc --noEmit`

**Files:**
- Create: `src/agent_harness/stacks/javascript/type_check.py`
- Create: `tests/stacks/javascript/test_type_check.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/stacks/javascript/test_type_check.py
import json
from unittest.mock import patch, MagicMock
from agent_harness.stacks.javascript.type_check import run_type_check, detect_framework


def test_detect_astro(tmp_path):
    pkg = {"dependencies": {"astro": "^6.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    assert detect_framework(tmp_path) == "astro"


def test_detect_next(tmp_path):
    pkg = {"dependencies": {"next": "^15.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    assert detect_framework(tmp_path) == "next"


def test_detect_default(tmp_path):
    pkg = {"dependencies": {"express": "^4.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    assert detect_framework(tmp_path) is None


def test_astro_uses_astro_check(tmp_path):
    pkg = {"dependencies": {"astro": "^6.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    with patch("agent_harness.stacks.javascript.type_check.shutil.which", return_value="/usr/bin/astro"):
        with patch("agent_harness.stacks.javascript.type_check.run_check") as mock_run:
            mock_run.return_value = MagicMock(passed=True, name="typecheck")
            run_type_check(tmp_path)
            cmd = mock_run.call_args[0][1]
            assert "astro" in cmd and "check" in cmd


def test_fallback_uses_tsc(tmp_path):
    pkg = {"dependencies": {"express": "^4.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    with patch("agent_harness.stacks.javascript.type_check.shutil.which", return_value="/usr/bin/tsc"):
        with patch("agent_harness.stacks.javascript.type_check.run_check") as mock_run:
            mock_run.return_value = MagicMock(passed=True, name="typecheck")
            run_type_check(tmp_path)
            cmd = mock_run.call_args[0][1]
            assert "tsc" in cmd
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/stacks/javascript/test_type_check.py -v`
Expected: FAIL

- [ ] **Step 3: Implement type_check.py**

```python
# src/agent_harness/stacks/javascript/type_check.py
"""
Framework-aware TypeScript type checking.

WHAT: Runs the best available type checker for the detected JS framework.
Astro → `astro check`. Next.js → `next lint`. Default → `tsc --noEmit`.

WHY: Framework-specific type checkers understand their own file types (.astro,
.vue) and catch errors that plain tsc misses. Agents generate components with
wrong prop types, missing imports, and broken content collection schemas.
Framework checkers catch these; tsc alone does not.

WITHOUT IT: Type errors in .astro/.vue files go undetected, broken component
props ship silently, content collection schema violations only surface at build.

FIX: Fix the type errors reported. For Astro, see https://docs.astro.build/en/guides/typescript/

REQUIRES: Framework CLI (astro, next) or tsc, via PATH or npx fallback
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil

from agent_harness.runner import run_check, CheckResult

# Framework detection: package name → framework key
FRAMEWORK_DEPS = {
    "astro": "astro",
    "next": "next",
    "nuxt": "nuxt",
}


def detect_framework(project_dir: Path) -> str | None:
    """Detect JS framework from package.json dependencies."""
    pkg_path = project_dir / "package.json"
    if not pkg_path.exists():
        return None
    try:
        pkg = json.loads(pkg_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    for dep, framework in FRAMEWORK_DEPS.items():
        if dep in all_deps:
            return framework
    return None


def run_type_check(project_dir: Path) -> CheckResult:
    """Run the best available type checker for this project."""
    framework = detect_framework(project_dir)

    if framework == "astro":
        if shutil.which("astro"):
            return run_check("typecheck:astro", ["astro", "check"], cwd=str(project_dir))
        return run_check("typecheck:astro", ["npx", "astro", "check"], cwd=str(project_dir))

    if framework == "next":
        if shutil.which("next"):
            return run_check("typecheck:next", ["next", "lint"], cwd=str(project_dir))
        return run_check("typecheck:next", ["npx", "next", "lint"], cwd=str(project_dir))

    # Default: tsc
    if shutil.which("tsc"):
        return run_check("typecheck:tsc", ["tsc", "--noEmit"], cwd=str(project_dir))
    return run_check("typecheck:tsc", ["npx", "tsc", "--noEmit"], cwd=str(project_dir))
```

- [ ] **Step 4: Run tests**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/stacks/javascript/test_type_check.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent_harness/stacks/javascript/type_check.py tests/stacks/javascript/test_type_check.py
git commit -m "feat: framework-aware type checking — astro check, next lint, tsc fallback"
```

---

### Task 8: package.json Rego policies

Enforce basic package.json hygiene: `engines` field present, `type: "module"` for ESM, no `*` wildcard versions.

**Files:**
- Create: `policies/javascript/package.rego`
- Create: `policies/javascript/package_test.rego`

- [ ] **Step 1: Write Rego policy**

```rego
# policies/javascript/package.rego
package javascript.package

# PACKAGE.JSON — engines, type, version hygiene
#
# WHAT: Ensures package.json has `engines` field, `type: "module"`,
# and no wildcard `*` version ranges.
#
# WHY (engines): Without `engines`, the project runs on any Node version.
# Agents and CI may use incompatible versions — code works locally but breaks
# in deployment. `engines` makes version requirements explicit and enforceable.
#
# WHY (type): Node defaults to CommonJS. Mixed ESM/CJS causes confusing errors.
# Explicit `type: "module"` prevents agents from accidentally mixing module systems.
#
# WHY (no wildcards): `*` versions accept anything, including breaking majors.
# Agents run `npm install` and get different versions each time.
#
# WITHOUT IT: "Works on my machine" Node version issues, mixed module system
# errors, non-deterministic dependency resolution.
#
# FIX: Add "engines": {"node": ">=22"}, "type": "module" to package.json.
# Replace * versions with explicit ranges (^x.y.z).
#
# Input: parsed package.json (JSON)

import rego.v1

# ── Policy: engines field must exist ──

deny contains msg if {
	not input.engines
	msg := "package.json: missing 'engines' field — specify Node version to prevent version mismatch"
}

# ── Policy: type should be "module" ──

warn contains msg if {
	not input.type
	msg := "package.json: missing 'type' field — add '\"type\": \"module\"' for explicit ESM"
}

warn contains msg if {
	input.type
	input.type != "module"
	msg := sprintf("package.json: 'type' is '%s', consider 'module' for ESM consistency", [input.type])
}

# ── Policy: no wildcard versions in dependencies ──

deny contains msg if {
	some dep, version in input.dependencies
	version == "*"
	msg := sprintf("package.json: dependency '%s' has wildcard version '*' — pin to explicit range", [dep])
}

deny contains msg if {
	some dep, version in input.devDependencies
	version == "*"
	msg := sprintf("package.json: devDependency '%s' has wildcard version '*' — pin to explicit range", [dep])
}
```

- [ ] **Step 2: Write Rego tests**

```rego
# policies/javascript/package_test.rego
package javascript.package_test

import data.javascript.package
import rego.v1

# ── engines ──

test_missing_engines_denied if {
	count(package.deny) > 0 with input as {"name": "x", "version": "1.0.0"}
}

test_engines_present_passes if {
	denials := package.deny with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"type": "module",
	}
	count(denials) == 0
}

# ── type: module ──

test_missing_type_warned if {
	count(package.warn) > 0 with input as {
		"name": "x",
		"engines": {"node": ">=22"},
	}
}

test_type_module_no_warning if {
	warnings := package.warn with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"type": "module",
	}
	count(warnings) == 0
}

# ── wildcard versions ──

test_wildcard_dep_denied if {
	count(package.deny) > 0 with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"dependencies": {"bad-pkg": "*"},
	}
}

test_pinned_dep_passes if {
	denials := package.deny with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"type": "module",
		"dependencies": {"good-pkg": "^1.2.3"},
	}
	count(denials) == 0
}

test_wildcard_devdep_denied if {
	count(package.deny) > 0 with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"devDependencies": {"bad-dev": "*"},
	}
}
```

- [ ] **Step 3: Run Rego tests**

Run: `cd ~/Workspaces/ai-harness && conftest verify -p policies/javascript/ --no-color`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add policies/javascript/
git commit -m "feat: package.json Rego policies — engines, type:module, no wildcard versions"
```

---

### Task 9: Conftest package.json check (Python wrapper)

**Files:**
- Create: `src/agent_harness/stacks/javascript/conftest_package_check.py`
- Create: `tests/stacks/javascript/test_conftest_package_check.py`

- [ ] **Step 1: Write failing test**

```python
# tests/stacks/javascript/test_conftest_package_check.py
from agent_harness.stacks.javascript.conftest_package_check import run_conftest_package


def test_skips_when_no_package_json(tmp_path):
    result = run_conftest_package(tmp_path)
    assert result.passed
    assert "Skipping" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/stacks/javascript/test_conftest_package_check.py -v`
Expected: FAIL

- [ ] **Step 3: Implement conftest_package_check.py**

```python
# src/agent_harness/stacks/javascript/conftest_package_check.py
"""
Conftest package.json check.

WHAT: Runs conftest on package.json with bundled JavaScript policies to enforce
engines field, ESM type, and version hygiene.

WHY: Agents create package.json files missing critical fields (engines, type)
and use wildcard versions. These misconfigurations cause "works on my machine"
failures and non-deterministic dependency resolution.

WITHOUT IT: Node version mismatches in CI/deploy, mixed ESM/CJS module errors,
different dependency versions on every npm install.

FIX: Run `agent-harness audit` to see specific package.json issues.

REQUIRES: conftest (via PATH)
"""
from __future__ import annotations

from pathlib import Path

from agent_harness.runner import CheckResult, run_check

POLICIES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "policies"


def run_conftest_package(project_dir: Path) -> CheckResult:
    """Run conftest on package.json with bundled javascript policies."""
    target = project_dir / "package.json"
    if not target.exists():
        return CheckResult(
            name="conftest-package",
            passed=True,
            output="Skipping conftest-package: package.json not found",
        )
    policy_path = POLICIES_DIR / "javascript"
    cmd = [
        "conftest", "test", str(target),
        "--policy", str(policy_path),
        "--no-color", "--all-namespaces",
    ]
    return run_check("conftest-package", cmd, cwd=str(project_dir))
```

- [ ] **Step 4: Run tests**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/stacks/javascript/test_conftest_package_check.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent_harness/stacks/javascript/conftest_package_check.py tests/stacks/javascript/test_conftest_package_check.py
git commit -m "feat: conftest wrapper for package.json Rego policies"
```

---

### Task 10: Wire JS stack into lint, fix, audit, init

Connect all the new JS checks into the CLI pipeline.

**Files:**
- Modify: `src/agent_harness/lint.py`
- Modify: `src/agent_harness/fix.py`
- Modify: `src/agent_harness/audit.py`
- Modify: `src/agent_harness/config.py`
- Modify: `src/agent_harness/init/templates.py`
- Create: `src/agent_harness/stacks/javascript/templates.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Add JavaScriptConfig to config.py**

```python
@dataclass
class JavaScriptConfig:
    coverage_threshold: int = 80


@dataclass
class HarnessConfig:
    stacks: set[str] = field(default_factory=set)
    exclude: list[str] = field(default_factory=list)
    python: PythonConfig = field(default_factory=PythonConfig)
    docker: DockerConfig = field(default_factory=DockerConfig)
    javascript: JavaScriptConfig = field(default_factory=JavaScriptConfig)
```

Add to `load_config()`:
```python
if "javascript" in raw:
    for k, v in raw["javascript"].items():
        if hasattr(config.javascript, k):
            setattr(config.javascript, k, v)
```

- [ ] **Step 2: Wire JS checks into lint.py**

Add imports and JS block:
```python
from agent_harness.stacks.javascript.biome_check import run_biome
from agent_harness.stacks.javascript.type_check import run_type_check
from agent_harness.stacks.javascript.conftest_package_check import run_conftest_package

# ... inside run_lint(), after docker checks:

    # JavaScript checks
    if "javascript" in config.stacks:
        results.extend(run_biome(project_dir))
        results.append(run_type_check(project_dir))
        results.append(run_conftest_package(project_dir))
```

- [ ] **Step 3: Add biome fix to fix.py**

Refactor `run_fix` to be stack-aware:
```python
from agent_harness.config import load_config

def run_fix(project_dir: Path) -> list[str]:
    """Auto-fix what's fixable, then return actions taken."""
    actions = []
    config = load_config(project_dir)

    # Python: ruff fix
    if "python" in config.stacks:
        if shutil.which("ruff"):
            fix_cmd = ["ruff", "check", "--fix"]
            fmt_cmd = ["ruff", "format"]
        else:
            fix_cmd = ["uv", "run", "ruff", "check", "--fix"]
            fmt_cmd = ["uv", "run", "ruff", "format"]

        result = run_check("ruff:fix", fix_cmd, cwd=str(project_dir))
        if result.passed:
            actions.append("ruff: auto-fixed lint issues")
        elif "not found" in result.error.lower():
            actions.append("ruff: not installed, skipping fix")

        result = run_check("ruff:format", fmt_cmd, cwd=str(project_dir))
        if result.passed:
            actions.append("ruff: formatted code")
        elif "not found" in result.error.lower():
            actions.append("ruff: not installed, skipping format")

    # JavaScript: biome fix
    if "javascript" in config.stacks:
        if shutil.which("biome"):
            biome_cmd = ["biome", "check", "--fix", "."]
        else:
            biome_cmd = ["npx", "@biomejs/biome", "check", "--fix", "."]

        result = run_check("biome:fix", biome_cmd, cwd=str(project_dir))
        if result.passed:
            actions.append("biome: auto-fixed lint and format issues")
        elif "not found" in result.error.lower():
            actions.append("biome: not installed, skipping fix")

    return actions
```

- [ ] **Step 4: Add JS tools to audit.py**

Add after existing Python tools block in `run_audit()`:
Also fix the existing gitignore audit call to pass stacks (needed after Task 3's signature change). In the `.gitignore` section of `audit.py`, change `run_conftest_gitignore(project_dir)` to `run_conftest_gitignore(project_dir, stacks=stacks)`.

```python
if "javascript" in stacks:
    tools["biome"] = "npm install --save-dev @biomejs/biome"

# JavaScript-specific: package.json audit
if "javascript" in stacks:
    pkg = project_dir / "package.json"
    if pkg.exists():
        from agent_harness.stacks.javascript.conftest_package_check import run_conftest_package
        result = run_conftest_package(project_dir)
        if result.passed:
            items.append(AuditItem(area="javascript", status="ok", message="package.json harness config correct"))
        else:
            items.append(AuditItem(area="javascript", status="misconfigured", message="package.json issues", fix=result.output or result.error))
```

- [ ] **Step 5: Create JS templates**

```python
# src/agent_harness/stacks/javascript/templates.py
"""Config templates for JavaScript/TypeScript stack."""

BIOME_CONFIG = """\
{
  "$schema": "https://biomejs.dev/schemas/2.0.0/schema.json",
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true
    }
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  }
}
"""

TSCONFIG_STRICT = """\
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "noUncheckedIndexedAccess": true,
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "skipLibCheck": true
  }
}
"""
```

- [ ] **Step 6: Update init templates**

Update `HARNESS_YML` in `src/agent_harness/init/templates.py`:
```python
HARNESS_YML = """\
# AI Harness configuration
# Detected stacks: {stacks}
stacks: [{stacks_list}]

# exclude:
#   - _archive/
#   - vendor/

# python:
#   coverage_threshold: 95
#   line_length: 140

# javascript:
#   coverage_threshold: 80

# docker:
#   own_image_prefix: "ghcr.io/myorg/"
"""
```

- [ ] **Step 7: Add config test for JavaScriptConfig**

Add to `tests/test_config.py`:
```python
def test_load_config_javascript(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}')
    (tmp_path / ".agent-harness.yml").write_text(
        "stacks: [javascript]\njavascript:\n  coverage_threshold: 90\n"
    )
    config = load_config(tmp_path)
    assert "javascript" in config.stacks
    assert config.javascript.coverage_threshold == 90


def test_load_config_javascript_defaults(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}')
    config = load_config(tmp_path)
    assert "javascript" in config.stacks
    assert config.javascript.coverage_threshold == 80
```

- [ ] **Step 8: Run all tests**

Run: `cd ~/Workspaces/ai-harness && uv run pytest tests/ -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add src/agent_harness/lint.py src/agent_harness/fix.py src/agent_harness/audit.py src/agent_harness/config.py src/agent_harness/init/templates.py src/agent_harness/stacks/javascript/templates.py tests/test_config.py
git commit -m "feat: wire JavaScript stack into lint, fix, audit, init pipeline"
```

---

### Task 11: Integration test — run on the blog

Verify the full pipeline works on `~/Workspaces/iorlas.github.io`.

**No new files — validation only.**

- [ ] **Step 1: Reinstall agent-harness**

```bash
cd ~/Workspaces/ai-harness && uv tool install -e . --force
```

- [ ] **Step 2: Run detect on blog**

```bash
cd ~/Workspaces/iorlas.github.io && agent-harness detect
```
Expected: `javascript` (and NOT `python`)

- [ ] **Step 3: Run lint on blog**

```bash
cd ~/Workspaces/iorlas.github.io && agent-harness lint
```
Expected:
- `conftest-gitignore` should NOT flag `.venv` or `__pycache__`
- `conftest-json` should NOT choke on `tsconfig.json`
- `yamllint` should NOT scan `pnpm-lock.yaml` or `_archive/`
- `conftest-package` should report on `package.json` (missing `type: "module"` as warn)
- Biome and type checks may fail (tools not installed) — that's expected, error should be clear

- [ ] **Step 4: Run audit on blog**

```bash
cd ~/Workspaces/iorlas.github.io && agent-harness audit
```
Expected: Reports biome as missing, shows JS-specific advice

- [ ] **Step 5: Compare timing**

```bash
cd ~/Workspaces/iorlas.github.io && time agent-harness lint
```
Expected: Significantly faster than previous 2.5s (yamllint lock file issue resolved)

- [ ] **Step 6: Run all agent-harness tests to ensure nothing regressed**

```bash
cd ~/Workspaces/ai-harness && uv run pytest tests/ -v && conftest verify -p policies/ --no-color
```
Expected: ALL PASS

- [ ] **Step 7: Update PLANS.md**

Move "JavaScript/TypeScript stack module" from v0.3+ to Done. Add notes about Biome, framework detection, file exclusions.

- [ ] **Step 8: Final commit**

```bash
git add PLANS.md
git commit -m "docs: mark JavaScript stack as implemented, update roadmap"
```
