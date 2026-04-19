# agent-weiss Control Library Build-Out (Plan 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the relevant subset of agent-harness Rego policies (those that fit v1 profiles: universal/python/typescript) and add the missing v1 controls so the bundle ships ~16 controls total following the canonical pattern from Plan 1.

**Architecture:** Each control gets its own directory under `profiles/<profile>/domains/<domain>/controls/<control>/` containing `prescribed.yaml + check.sh + instruct.md` (+ `policy.rego` + `policy_test.rego` for Rego-based controls) + matching `fixtures/profiles/.../<control>/{pass,fail}/` fixtures. Rego-based controls share a Python helper (`agent_weiss.lib.rego`) and a thin shell wrapper (`scripts/run_rego_check.sh`) that invoke `conftest`, parse its JSON output, and emit the agent-weiss JSON contract from Plan 1 Task 7.

**Tech Stack:**
- Python 3.12+ (helper modules, tests)
- `uv` (already wired)
- `pytest` (existing parametric runners auto-discover new controls)
- `conftest` 0.56+ (Rego policy execution, already installed in CI)
- POSIX shell (`check.sh` files)
- Rego (`policy.rego` files)

**Repository:** `/Users/iorlas/Workspaces/agent-weiss` (created in Plan 1; tagged `foundations-mvp`).

**Spec / roadmap:**
- `docs/superpowers/specs/2026-04-14-agent-weiss-design.md`
- `docs/superpowers/plans/2026-04-14-agent-weiss-roadmap.md` (cross-cutting decisions live here — DO NOT restate in this plan)
- `docs/superpowers/plans/2026-04-14-agent-weiss-foundations.md` (Plan 1, completed)

**Plan scope (in):**
- Python + Typescript profile manifests
- Shared Rego runner infrastructure (Python helper + shell wrapper)
- Fixture runner env update (set `AGENT_WEISS_BUNDLE` for subprocess)
- 6 ported controls (4 python + 1 universal security + 1 typescript structure)
- 9 new controls (3 universal docs/security new entries + 2 universal vcs + 1 python ty + 1 typescript biome + 1 typescript vitest + 1 universal docs/security extra)
- Updated `instruct.md` for each control
- Each control adds `pass/` and `fail/` fixtures so the Plan 1 parametric tests stay green

**Plan scope (out — handled later):**
- Approval UX polish (Plan 3)
- Verify workflow + scoring (Plan 4)
- Distribution packaging + bundle.yaml file index regeneration (Plan 5)
- Drift refresh UX (Plan 6)
- docker/compose/dokploy profiles (deferred to v2 per roadmap §Scope)
- Hardening items flagged in Plan 1's final review (deepcopy `_raw`, schema version checking, recursive orphan scan) — defer to a separate hardening plan before Plan 4

**Migration source inventory** (agent-harness Rego policies, in `/Users/iorlas/Workspaces/agent-harness/src/agent_harness/policies/`):

| Source policy | Migrate? | Target control |
|---|---|---|
| `python/ruff.rego` | yes | `python.quality.ruff-config` |
| `python/pytest.rego` | yes | `python.testing.pytest-config` |
| `python/coverage.rego` | yes | `python.testing.coverage-threshold` |
| `python/test_isolation.rego` | yes | `python.testing.test-isolation` |
| `gitignore/secrets.rego` | yes | `universal.security.gitignore-secrets` |
| `javascript/package.rego` | yes | `typescript.project-structure.package-json` |
| `compose/*` (6) | no — docker deferred to v2 | — |
| `dockerfile/*` (6) | no — docker deferred to v2 | — |
| `dokploy/traefik.rego` | no — out of v1 profiles | — |

**v1 control inventory after Plan 2** (16 total):

| Profile | Domain | Control | Source |
|---|---|---|---|
| universal | docs | agents-md-present | Plan 1 |
| universal | docs | claude-md-present | new (this plan) |
| universal | docs | readme-present | new |
| universal | security | gitignore-secrets | ported |
| universal | security | env-files-not-tracked | new |
| universal | security | gitleaks-precommit | new |
| universal | vcs | gitignore-present | new |
| universal | vcs | license-present | new |
| python | quality | ruff-config | ported |
| python | quality | ty-config | new |
| python | testing | pytest-config | ported |
| python | testing | coverage-config | ported |
| python | testing | test-isolation | ported |
| typescript | project-structure | package-json | ported |
| typescript | quality | biome-config | new |
| typescript | testing | vitest-config | new |

---

## Pause points

This plan has natural checkpoints where the user may stop and continue later. Each checkpoint leaves agent-weiss in a CI-green state with a coherent subset of controls shipped. After each checkpoint, run the full suite (`uv run pytest -v`) and confirm CI green before pausing.

- **After Task 3:** infrastructure ready (profile manifests + Rego runner). 0 new controls shipped yet.
- **After Task 10:** all 7 universal controls shipped (8 total with Plan 1's agents-md-present).
- **After Task 15:** all python controls shipped.
- **After Task 18:** all typescript controls shipped — full v1 control library complete.
- **After Task 20:** roadmap updated, tag pushed. Plan 2 complete.

---

## Task 1: Python profile manifest

**Files:**
- Create: `profiles/python/manifest.yaml`

The python profile groups all controls applicable to projects with `pyproject.toml`. Plan 1 only created the universal manifest; this task adds python.

- [ ] **Step 1: Create the manifest**

Create `/Users/iorlas/Workspaces/agent-weiss/profiles/python/manifest.yaml`:

```yaml
profile: python
description: Standards for Python projects (detected via pyproject.toml at the repo root).
domains:
  - quality
  - testing
```

- [ ] **Step 2: Verify the existing pytest suite still passes (no new controls yet)**

Run:
```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest -v
```

Expected: 36 passed (no change — manifest alone doesn't add tests).

- [ ] **Step 3: Commit**

```bash
git add profiles/python/manifest.yaml
git commit -m "feat: python profile manifest"
git push
```

---

## Task 2: Typescript profile manifest

**Files:**
- Create: `profiles/typescript/manifest.yaml`

- [ ] **Step 1: Create the manifest**

Create `/Users/iorlas/Workspaces/agent-weiss/profiles/typescript/manifest.yaml`:

```yaml
profile: typescript
description: Standards for TypeScript / JavaScript projects (detected via package.json at the repo root).
domains:
  - project-structure
  - quality
  - testing
```

- [ ] **Step 2: Run pytest**

Run:
```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest -v
```

Expected: 36 passed.

- [ ] **Step 3: Commit**

```bash
git add profiles/typescript/manifest.yaml
git commit -m "feat: typescript profile manifest"
git push
```

---

## Task 3: Rego runner infrastructure

**Files:**
- Create: `src/agent_weiss/lib/rego.py`
- Create: `scripts/run_rego_check.sh` (executable)
- Create: `tests/test_rego.py`
- Modify: `tests/test_fixture_runner.py` (set `AGENT_WEISS_BUNDLE` env)

This task provides the shared infrastructure every Rego-based control depends on. It implements:
1. A Python module `agent_weiss.lib.rego` that runs `conftest test`, parses its JSON output, and returns a CheckResult-shaped result.
2. A thin shell wrapper `scripts/run_rego_check.sh` that each Rego control's `check.sh` will invoke (avoids 9 controls duplicating shell logic).
3. An update to the existing fixture runner so subprocess invocations get `AGENT_WEISS_BUNDLE` set to the repo root (Rego controls need it to find their policy files).

TDD strict: tests fail first, then implement.

- [ ] **Step 1: Write the failing test**

Create `tests/test_rego.py`:

```python
"""Tests for the shared Rego runner helper."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from agent_weiss.lib.rego import run_rego_check


REPO_ROOT = Path(__file__).resolve().parent.parent


def _conftest_available() -> bool:
    return shutil.which("conftest") is not None


@pytest.mark.skipif(not _conftest_available(), reason="conftest not installed")
def test_rego_pass(tmp_path: Path):
    """Project file satisfies the policy → status=pass, exit 0."""
    policy = tmp_path / "policy.rego"
    policy.write_text(
        "package x\n"
        "import rego.v1\n"
        "deny contains msg if {\n"
        "  not input.foo\n"
        "  msg := \"missing foo\"\n"
        "}\n"
    )
    target = tmp_path / "input.json"
    target.write_text(json.dumps({"foo": "bar"}))

    result = run_rego_check(target=target, policy=policy)
    assert result["status"] == "pass"
    assert result["findings_count"] == 0


@pytest.mark.skipif(not _conftest_available(), reason="conftest not installed")
def test_rego_fail_with_findings(tmp_path: Path):
    """Project file violates policy → status=fail, findings_count matches deny count."""
    policy = tmp_path / "policy.rego"
    policy.write_text(
        "package x\n"
        "import rego.v1\n"
        "deny contains msg if {\n"
        "  not input.foo\n"
        "  msg := \"missing foo\"\n"
        "}\n"
        "deny contains msg if {\n"
        "  not input.bar\n"
        "  msg := \"missing bar\"\n"
        "}\n"
    )
    target = tmp_path / "input.json"
    target.write_text("{}")

    result = run_rego_check(target=target, policy=policy)
    assert result["status"] == "fail"
    assert result["findings_count"] == 2
    assert "missing foo" in result["summary"] or "missing bar" in result["summary"]


def test_rego_setup_unmet_when_conftest_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """If conftest binary not found, return setup-unmet with install hint."""
    # Force PATH to not contain conftest
    monkeypatch.setenv("PATH", "")
    policy = tmp_path / "policy.rego"
    policy.write_text("package x\nimport rego.v1\n")
    target = tmp_path / "input.json"
    target.write_text("{}")

    result = run_rego_check(target=target, policy=policy)
    assert result["status"] == "setup-unmet"
    assert "conftest" in result["install"].lower()


def test_rego_target_missing_returns_pass(tmp_path: Path):
    """If the target file doesn't exist (control not relevant), return pass with explanation."""
    policy = tmp_path / "policy.rego"
    policy.write_text("package x\nimport rego.v1\n")
    target = tmp_path / "nonexistent.json"

    result = run_rego_check(target=target, policy=policy)
    assert result["status"] == "pass"
    assert "not present" in result["summary"].lower() or "skipped" in result["summary"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_rego.py -v
```

Expected: 4 tests FAIL on import.

- [ ] **Step 3: Implement the Rego runner**

Create `src/agent_weiss/lib/rego.py`:

```python
"""Shared Rego runner — invoke conftest, parse JSON output, emit agent-weiss contract.

Each Rego-based control's check.sh delegates here via scripts/run_rego_check.sh.
This avoids 10+ controls duplicating the shell parsing logic.
"""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
from typing import TypedDict


class RegoResult(TypedDict, total=False):
    status: str  # "pass" | "fail" | "setup-unmet"
    findings_count: int
    summary: str
    install: str
    details_path: str


_INSTALL_HINT = (
    "Install conftest: brew install conftest (macOS) or "
    "see https://www.conftest.dev/install/"
)


def run_rego_check(
    target: Path,
    policy: Path,
    data: dict | None = None,
) -> RegoResult:
    """Run conftest against target with given policy. Return contract-shaped dict.

    Behavior:
    - target missing → status=pass with "not present" summary (control N/A)
    - conftest missing → status=setup-unmet with install hint
    - conftest fails to start → status=setup-unmet with stderr summary
    - conftest exits 0 → status=pass, findings_count=0
    - conftest reports failures → status=fail with count + first few messages
    """
    if not target.exists():
        return {
            "status": "pass",
            "findings_count": 0,
            "summary": f"{target.name} not present — control not applicable",
        }

    if shutil.which("conftest") is None:
        return {
            "status": "setup-unmet",
            "summary": "conftest binary not found on PATH",
            "install": _INSTALL_HINT,
        }

    cmd = [
        "conftest", "test",
        str(target),
        "--policy", str(policy),
        "--no-color",
        "--all-namespaces",
        "--output", "json",
    ]
    data_path: Path | None = None
    if data is not None:
        data_path = target.parent / ".agent-weiss-rego-data.json"
        data_path.write_text(json.dumps(data))
        cmd.extend(["--data", str(data_path)])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return {
            "status": "setup-unmet",
            "summary": "conftest binary not found on PATH",
            "install": _INSTALL_HINT,
        }
    finally:
        if data_path is not None and data_path.exists():
            data_path.unlink()

    return _parse_conftest_output(proc.stdout, proc.returncode)


def _parse_conftest_output(stdout: str, returncode: int) -> RegoResult:
    """Parse conftest's JSON output. Return contract-shaped dict."""
    try:
        records = json.loads(stdout) if stdout.strip() else []
    except json.JSONDecodeError:
        return {
            "status": "setup-unmet",
            "summary": f"conftest produced unparseable output (exit {returncode})",
            "install": _INSTALL_HINT,
        }

    failures: list[str] = []
    for record in records:
        for failure in record.get("failures") or []:
            msg = failure.get("msg", "<no msg>")
            failures.append(msg)

    if not failures:
        return {
            "status": "pass",
            "findings_count": 0,
            "summary": "all policy checks passed",
        }

    preview = "; ".join(failures[:3])
    if len(failures) > 3:
        preview += f"; and {len(failures) - 3} more"
    return {
        "status": "fail",
        "findings_count": len(failures),
        "summary": preview,
    }
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/test_rego.py -v
```

Expected: 4 tests PASS (3 if `conftest` not locally installed — 2 will be skipped). Run full suite:
```bash
uv run pytest -v
```
Expected: 40 tests (36 prior + 4 new).

- [ ] **Step 5: Create the shell wrapper**

Create `/Users/iorlas/Workspaces/agent-weiss/scripts/` directory and `scripts/run_rego_check.sh`:

```sh
#!/bin/sh
# Shared Rego check.sh wrapper.
#
# Usage (from a control's check.sh):
#   sh "$AGENT_WEISS_BUNDLE/scripts/run_rego_check.sh" \
#     <target_relative_to_cwd> <policy_subpath_relative_to_bundle> [<data_json>]
#
# Reads $AGENT_WEISS_BUNDLE; emits one JSON line per the agent-weiss contract;
# exits 0 / 1 / 127 matching the JSON status.

set -e

if [ -z "$AGENT_WEISS_BUNDLE" ]; then
  printf '%s\n' '{"status": "setup-unmet", "summary": "AGENT_WEISS_BUNDLE not set", "install": "Install agent-weiss via Claude marketplace, PyPI, or npm — or set AGENT_WEISS_BUNDLE manually."}'
  exit 127
fi

TARGET="$1"
POLICY_SUBPATH="$2"
DATA_JSON="${3:-}"

if [ -z "$TARGET" ] || [ -z "$POLICY_SUBPATH" ]; then
  printf '%s\n' '{"status": "setup-unmet", "summary": "run_rego_check.sh requires <target> <policy_subpath> args"}'
  exit 127
fi

# Use the Python helper for parsing; relies on `python` being available.
# In dev: `uv run` provides it. In install scenarios: PyPI/npm bundles ship Python entry points (Plan 5).
PYTHON="${AGENT_WEISS_PYTHON:-python}"

EXIT_CODE=0
JSON_OUTPUT=$("$PYTHON" -c "
import json, sys
from pathlib import Path
from agent_weiss.lib.rego import run_rego_check

data = None
if '''$DATA_JSON''':
    data = json.loads('''$DATA_JSON''')

result = run_rego_check(
    target=Path('$TARGET'),
    policy=Path('$AGENT_WEISS_BUNDLE') / '$POLICY_SUBPATH',
    data=data,
)
print(json.dumps(result))
" ) || EXIT_CODE=$?

# If Python helper itself failed, emit setup-unmet
if [ "$EXIT_CODE" -ne 0 ] && [ -z "$JSON_OUTPUT" ]; then
  printf '%s\n' '{"status": "setup-unmet", "summary": "Python helper agent_weiss.lib.rego failed to run"}'
  exit 127
fi

# Map status to exit code
STATUS=$(printf '%s' "$JSON_OUTPUT" | "$PYTHON" -c "import json, sys; print(json.loads(sys.stdin.read())['status'])")

printf '%s\n' "$JSON_OUTPUT"

case "$STATUS" in
  pass) exit 0 ;;
  fail) exit 1 ;;
  setup-unmet) exit 127 ;;
  *) exit 1 ;;
esac
```

Make executable:
```bash
chmod +x /Users/iorlas/Workspaces/agent-weiss/scripts/run_rego_check.sh
```

- [ ] **Step 6: Update the fixture runner to set AGENT_WEISS_BUNDLE**

Modify `tests/test_fixture_runner.py`. Find both `subprocess.run` calls inside `test_control_passes_on_pass_fixture` and `test_control_fails_on_fail_fixture`. Add `env=` parameter that includes the existing environment plus `AGENT_WEISS_BUNDLE=<repo_root>`.

Replace the current subprocess.run calls with this pattern (apply to BOTH tests):

```python
import os

# At top of file, near other imports if not already there.

# Inside each test:
env = {**os.environ, "AGENT_WEISS_BUNDLE": str(REPO_ROOT)}
result = subprocess.run(
    ["sh", str(check_sh)],
    cwd=pass_dir,  # or fail_dir for the other test
    capture_output=True,
    text=True,
    env=env,
)
```

The existing assertion logic stays. Existing controls (Plan 1's `agents-md-present`) still pass — they don't read the env var.

- [ ] **Step 7: Run full suite**

```bash
uv run pytest -v
```

Expected: 40 tests pass (36 + 4 rego).

- [ ] **Step 8: Commit**

```bash
git add src/agent_weiss/lib/rego.py scripts/ tests/test_rego.py tests/test_fixture_runner.py
git commit -m "feat: shared Rego runner infrastructure for control library

- agent_weiss.lib.rego: invoke conftest, parse JSON, emit agent-weiss contract
- scripts/run_rego_check.sh: thin shell wrapper used by every Rego control
- tests/test_fixture_runner.py: set AGENT_WEISS_BUNDLE so Rego controls resolve their policy paths"
git push
```

---

## Task 4: universal.docs.claude-md-present

**Files (all new):**
- `profiles/universal/domains/docs/controls/claude-md-present/prescribed.yaml`
- `profiles/universal/domains/docs/controls/claude-md-present/check.sh` (executable)
- `profiles/universal/domains/docs/controls/claude-md-present/instruct.md`
- `fixtures/profiles/universal/domains/docs/controls/claude-md-present/pass/CLAUDE.md`
- `fixtures/profiles/universal/domains/docs/controls/claude-md-present/pass/README.md`
- `fixtures/profiles/universal/domains/docs/controls/claude-md-present/fail/README.md`

This is the simplest control type — pure shell, no Rego. Mirror of Plan 1's agents-md-present.

- [ ] **Step 1: Create prescribed.yaml**

```yaml
id: universal.docs.claude-md-present
version: 1
what: |
  Project has a CLAUDE.md file at the repository root.
why: |
  CLAUDE.md is Claude Code's standard for instructing the agent on project
  conventions, commands, and gotchas. Without it, Claude operates with no
  project-specific context and rediscovers everything every session.
applies_to:
  - any
```

- [ ] **Step 2: Create check.sh**

```sh
#!/bin/sh
# universal.docs.claude-md-present
if [ -f CLAUDE.md ]; then
  printf '%s\n' '{"status": "pass", "findings_count": 0, "summary": "CLAUDE.md present"}'
  exit 0
else
  printf '%s\n' '{"status": "fail", "findings_count": 1, "summary": "CLAUDE.md missing at project root"}'
  exit 1
fi
```

```bash
chmod +x profiles/universal/domains/docs/controls/claude-md-present/check.sh
```

- [ ] **Step 3: Create instruct.md**

```markdown
# Why CLAUDE.md

`CLAUDE.md` is Claude Code's project-context file. The agent reads it on every
session start; without it, Claude lacks project-specific conventions, dev
commands, and known gotchas — and rediscovers them session-by-session.

## What goes in it

- How to run the dev loop (`make dev`, `pnpm dev`, etc.)
- How to run tests (`make test`, `pytest`, etc.)
- File layout / naming conventions
- Commands the agent should prefer (e.g., "use `uv run` not `pip`")
- Gotchas the agent will hit if it doesn't know about them

## Relationship to AGENTS.md

`AGENTS.md` covers the same role for non-Claude agents (Codex, OpenCode).
Most content can be shared; keep tool-specific instructions in their own file.

## When to override

If your project deliberately doesn't use Claude Code (different agent only),
declare an override in `.agent-weiss.yaml` with a brief reason.
```

- [ ] **Step 4: Create the pass fixture**

`fixtures/profiles/universal/domains/docs/controls/claude-md-present/pass/CLAUDE.md`:
```markdown
# Project Claude instructions

Run `make test` to verify changes.
```

`fixtures/profiles/universal/domains/docs/controls/claude-md-present/pass/README.md`:
```markdown
# Pass fixture for universal.docs.claude-md-present
```

- [ ] **Step 5: Create the fail fixture**

`fixtures/profiles/universal/domains/docs/controls/claude-md-present/fail/README.md`:
```markdown
# Fail fixture for universal.docs.claude-md-present

Intentionally omits CLAUDE.md.
```

- [ ] **Step 6: Run pytest**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest -v
```

Expected: 45 tests pass (40 prior + 2 new fixture-runner + 3 new completeness self-tests for this control). Confirm parametrize IDs include the new control path.

- [ ] **Step 7: Commit**

```bash
git add profiles/universal/domains/docs/controls/claude-md-present/ \
        fixtures/profiles/universal/domains/docs/controls/claude-md-present/
git commit -m "feat: universal.docs.claude-md-present control"
git push
```

---

## Task 5: universal.docs.readme-present

**Files (new):**
- `profiles/universal/domains/docs/controls/readme-present/{prescribed.yaml,check.sh,instruct.md}`
- `fixtures/profiles/universal/domains/docs/controls/readme-present/{pass,fail}/`

- [ ] **Step 1: Create prescribed.yaml**

`profiles/universal/domains/docs/controls/readme-present/prescribed.yaml`:
```yaml
id: universal.docs.readme-present
version: 1
what: |
  Project has a README at the repository root (README.md, README.rst, or README).
why: |
  Without a README, both humans and agents lack the entry point that explains
  what the project is, how to run it, and how to contribute. Agents heuristically
  read README first when scanning a new repo.
applies_to:
  - any
```

- [ ] **Step 2: Create check.sh**

```sh
#!/bin/sh
# universal.docs.readme-present — accept any conventional README spelling.
for candidate in README.md README.rst README.txt README; do
  if [ -f "$candidate" ]; then
    printf '%s\n' '{"status": "pass", "findings_count": 0, "summary": "README present at project root"}'
    exit 0
  fi
done
printf '%s\n' '{"status": "fail", "findings_count": 1, "summary": "no README.* found at project root"}'
exit 1
```

```bash
chmod +x profiles/universal/domains/docs/controls/readme-present/check.sh
```

- [ ] **Step 3: Create instruct.md**

```markdown
# Why README

A README is the universal entry point. Both humans and AI agents reach for
README first when scanning an unfamiliar repository — what is this project,
how do I run it, where's the doc index, who maintains it.

## What it should contain

- One-line project description (what + why)
- Quick start: install + run commands
- Link to deeper docs if they exist (`docs/` folder, wiki, etc.)
- License + contribution pointer if open source

## When to override

A repository that's exclusively a Cargo, npm, or other registry artifact and
relies on the registry's auto-rendered description may legitimately skip
top-level README. Declare an override with that reason.
```

- [ ] **Step 4: Create pass fixture**

`fixtures/profiles/universal/domains/docs/controls/readme-present/pass/README.md`:
```markdown
# Pass fixture project

Quick start: `make dev`.
```

- [ ] **Step 5: Create fail fixture**

`fixtures/profiles/universal/domains/docs/controls/readme-present/fail/.keep`:
```
intentionally empty — no README of any kind
```

(Use `.keep` because git doesn't track empty dirs.)

- [ ] **Step 6: Run pytest**

```bash
uv run pytest -v
```

Expected: 50 tests pass (45 + 2 fixture + 3 completeness).

- [ ] **Step 7: Commit**

```bash
git add profiles/universal/domains/docs/controls/readme-present/ \
        fixtures/profiles/universal/domains/docs/controls/readme-present/
git commit -m "feat: universal.docs.readme-present control"
git push
```

---

## Task 6: universal.security.gitignore-secrets (Rego port)

**Files (new):**
- `profiles/universal/domains/security/controls/gitignore-secrets/{prescribed.yaml,check.sh,instruct.md,policy.rego,policy_test.rego}`
- `fixtures/profiles/universal/domains/security/controls/gitignore-secrets/{pass,fail}/.gitignore`

This is the first Rego-based migration. Source: `agent-harness/src/agent_harness/policies/gitignore/secrets.rego`.

For Plan 2 simplicity, drop the stack-aware branches (Python/JS specific patterns) — those move to per-profile controls in a later plan. This control enforces only the universal rule: `.env` must be gitignored.

- [ ] **Step 1: Write the failing fixture (anticipates the runner)**

The fixture runner from Plan 1 will discover this control once `pass/` and `fail/` exist with check.sh-resolvable layout. Skip writing a separate test — Plan 1's parametric runner is the test.

Create `fixtures/profiles/universal/domains/security/controls/gitignore-secrets/pass/.gitignore`:
```
.env
.env.*
```

Create `fixtures/profiles/universal/domains/security/controls/gitignore-secrets/fail/.gitignore`:
```
*.log
node_modules/
```

- [ ] **Step 2: Create prescribed.yaml**

`profiles/universal/domains/security/controls/gitignore-secrets/prescribed.yaml`:
```yaml
id: universal.security.gitignore-secrets
version: 1
what: |
  Project's .gitignore excludes .env and .env.* files at the repo root.
why: |
  Agents (and humans) frequently create .env files containing real API keys,
  database URLs, and tokens. If .env is not gitignored, secrets leak into
  history on the next `git add .` or `git commit -a`. .gitignore is the
  cheapest, last-line-of-defense control against this entire class of leak.
applies_to:
  - any
install:
  macos: brew install conftest
  linux: see https://www.conftest.dev/install/
```

- [ ] **Step 3: Create policy.rego (Rego policy)**

`profiles/universal/domains/security/controls/gitignore-secrets/policy.rego`:
```rego
package universal.security.gitignore_secrets

# WHAT: .gitignore must exclude .env and .env.* files.
# WHY: Agents create .env with real secrets; without gitignore entries the
# next `git add .` leaks them.
# WITHOUT IT: Secrets in git history.
# FIX: Add `.env` and `.env.*` lines to .gitignore.
#
# Input: array of [{Kind, Value, Original}] entries from conftest's
# .gitignore parser.

import rego.v1

deny contains msg if {
	not _pattern_present(".env")
	msg := ".gitignore: '.env' is not excluded — agents create .env files containing real secrets"
}

deny contains msg if {
	not _pattern_present(".env.*")
	not _pattern_present(".env*")
	msg := ".gitignore: '.env.*' (or '.env*') is not excluded — variants like .env.local also leak secrets"
}

_pattern_present(pattern) if {
	some entry in input
	entry.Kind == "Path"
	entry.Value == pattern
}

_pattern_present(pattern) if {
	some entry in input
	entry.Kind == "Path"
	entry.Original == pattern
}
```

- [ ] **Step 4: Create policy_test.rego (Rego unit tests)**

`profiles/universal/domains/security/controls/gitignore-secrets/policy_test.rego`:
```rego
package universal.security.gitignore_secrets_test

import rego.v1
import data.universal.security.gitignore_secrets

test_missing_env_fires if {
	gitignore_secrets.deny with input as [
		{"Kind": "Path", "Value": "*.log", "Original": "*.log"},
	]
}

test_env_present_no_deny_for_dotenv if {
	count([msg | some msg in gitignore_secrets.deny; contains(msg, "'.env'")]) == 0 with input as [
		{"Kind": "Path", "Value": ".env", "Original": ".env"},
		{"Kind": "Path", "Value": ".env.*", "Original": ".env.*"},
	]
}

test_env_glob_present_no_deny_for_glob if {
	count([msg | some msg in gitignore_secrets.deny; contains(msg, "'.env.*'")]) == 0 with input as [
		{"Kind": "Path", "Value": ".env", "Original": ".env"},
		{"Kind": "Path", "Value": ".env.*", "Original": ".env.*"},
	]
}

test_only_env_no_glob_fires_glob_rule if {
	gitignore_secrets.deny with input as [
		{"Kind": "Path", "Value": ".env", "Original": ".env"},
	]
}
```

- [ ] **Step 5: Create check.sh (delegates to shared runner)**

`profiles/universal/domains/security/controls/gitignore-secrets/check.sh`:
```sh
#!/bin/sh
# universal.security.gitignore-secrets
# Delegates to shared Rego runner. Target: .gitignore (parsed by conftest).
exec sh "$AGENT_WEISS_BUNDLE/scripts/run_rego_check.sh" \
  ".gitignore" \
  "profiles/universal/domains/security/controls/gitignore-secrets/policy.rego"
```

```bash
chmod +x profiles/universal/domains/security/controls/gitignore-secrets/check.sh
```

- [ ] **Step 6: Create instruct.md**

`profiles/universal/domains/security/controls/gitignore-secrets/instruct.md`:
```markdown
# Why .env must be gitignored

Coding agents create `.env` files routinely — for local dev, for testing
with real API keys, for spinning up services. If `.env` is not in
`.gitignore`, the next `git add .` or `git commit -a` commits the secret.

By the time someone notices, the secret is in history. Rotating secrets
out of history is painful: BFG-repo-cleaner, force-push, every collaborator
re-clones. Prevention costs two lines in `.gitignore`.

## What to add

```
.env
.env.*
```

Some projects use a tracked `.env.example` template. Add it as an explicit
exception:
```
.env
.env.*
!.env.example
```

## When to override

If your project genuinely has no secrets and no .env workflow (rare, e.g.
a static site), you may override. Document the reason in `.agent-weiss.yaml`.

## Rego unit-test check

`policy_test.rego` exercises the deny rules in isolation. Run with
`conftest verify --policy policy.rego` from this directory.
```

- [ ] **Step 7: Run pytest**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest -v
```

Expected: 55 tests pass (50 + 2 fixture-runner + 3 completeness for this control).

If `conftest` is not installed locally, the pass fixture may report `setup-unmet` and `test_control_passes_on_pass_fixture` will fail. The fix: install conftest (`brew install conftest` on macOS) before running this task.

- [ ] **Step 8: Verify the Rego unit tests pass with conftest verify**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
conftest verify --policy profiles/universal/domains/security/controls/gitignore-secrets/policy.rego
```

Expected: `4 tests, 4 passed`.

- [ ] **Step 9: Commit**

```bash
git add profiles/universal/domains/security/controls/gitignore-secrets/ \
        fixtures/profiles/universal/domains/security/controls/gitignore-secrets/
git commit -m "feat: universal.security.gitignore-secrets (Rego port from agent-harness)"
git push
```

---

## Task 7: universal.security.env-files-not-tracked

**Files (new):**
- `profiles/universal/domains/security/controls/env-files-not-tracked/{prescribed.yaml,check.sh,instruct.md}`
- `fixtures/.../{pass,fail}/`

This is a runtime check: are any `.env*` files actually tracked in git? Plan 2 keeps it shell-only (no Rego). Pass fixture: empty directory (nothing tracked). Fail fixture: `.env` file present at root (would be tracked if committed).

For the fixture, since fixtures aren't a real git repo, use a heuristic: presence of `.env` anywhere in the working tree as a proxy. (Real-project use will refine this in Plan 3 with `git ls-files`-based logic.)

- [ ] **Step 1: Create prescribed.yaml**

```yaml
id: universal.security.env-files-not-tracked
version: 1
what: |
  No .env or .env.* files are present in the project working tree at any depth.
why: |
  Even with .gitignore, a developer or agent can `git add -f .env` and bypass
  the ignore rule. This control catches the artifact directly: if .env exists
  in-tree, the user must confirm it's not tracked, or rename it (.env.example).
applies_to:
  - any
```

- [ ] **Step 2: Create check.sh**

```sh
#!/bin/sh
# universal.security.env-files-not-tracked
# Walk the project tree for .env or .env.* files (excluding .env.example).
COUNT=$(find . -type f \( -name '.env' -o -name '.env.*' \) ! -name '.env.example' 2>/dev/null | wc -l | tr -d ' ')
if [ "$COUNT" = "0" ]; then
  printf '%s\n' '{"status": "pass", "findings_count": 0, "summary": "no .env files in tree"}'
  exit 0
else
  printf '%s\n' "{\"status\": \"fail\", \"findings_count\": $COUNT, \"summary\": \"$COUNT .env file(s) present in working tree — verify untracked or rename to .env.example\"}"
  exit 1
fi
```

```bash
chmod +x profiles/universal/domains/security/controls/env-files-not-tracked/check.sh
```

- [ ] **Step 3: Create instruct.md**

```markdown
# Why no .env files in working tree

`.gitignore` prevents accidental staging, but a forced `git add -f .env`
bypasses it. The deeper check: don't have a `.env` in the working tree
unless you actively need it.

## What to do

If you have a `.env`:
- Confirm it's not tracked: `git ls-files | grep .env` should return nothing
- Rename to `.env.example` if it's a template (no real secrets)
- Move to a tool-managed secrets store (1Password CLI, doppler, etc.) for
  real secrets

## Override

Active local dev with `.env` present is fine — declare an override with the
reason "active local-dev .env, gitignored, not for distribution."
```

- [ ] **Step 4: Pass fixture**

`fixtures/profiles/universal/domains/security/controls/env-files-not-tracked/pass/README.md`:
```markdown
# Pass fixture — no .env files
```

- [ ] **Step 5: Fail fixture**

`fixtures/profiles/universal/domains/security/controls/env-files-not-tracked/fail/.env`:
```
SECRET_KEY=fake-fail-fixture
```

- [ ] **Step 6: Run pytest**

```bash
uv run pytest -v
```

Expected: 60 tests (55 + 5).

- [ ] **Step 7: Commit**

```bash
git add profiles/universal/domains/security/controls/env-files-not-tracked/ \
        fixtures/profiles/universal/domains/security/controls/env-files-not-tracked/
git commit -m "feat: universal.security.env-files-not-tracked control"
git push
```

---

## Task 8: universal.security.gitleaks-precommit

**Files (new):**
- `profiles/universal/domains/security/controls/gitleaks-precommit/{prescribed.yaml,check.sh,instruct.md}`
- `fixtures/.../{pass,fail}/`

Checks that `.pre-commit-config.yaml` references gitleaks. Shell-only (grep). Real install command emitted on setup-unmet would be `pre-commit install` — but for this control we just check config presence.

- [ ] **Step 1: Create prescribed.yaml**

```yaml
id: universal.security.gitleaks-precommit
version: 1
what: |
  Project's .pre-commit-config.yaml includes a gitleaks hook entry.
why: |
  pre-commit + gitleaks blocks commits containing detected secrets before
  they leave the developer machine. This is a defense-in-depth layer below
  .gitignore — even if a secret slips past gitignore, gitleaks catches it
  on the commit hook.
applies_to:
  - any
install:
  macos: brew install pre-commit gitleaks
  linux: pip install pre-commit && (apt install gitleaks || nix-shell -p gitleaks)
```

- [ ] **Step 2: Create check.sh**

```sh
#!/bin/sh
# universal.security.gitleaks-precommit
if [ ! -f .pre-commit-config.yaml ]; then
  printf '%s\n' '{"status": "fail", "findings_count": 1, "summary": ".pre-commit-config.yaml missing"}'
  exit 1
fi
if grep -q 'gitleaks' .pre-commit-config.yaml; then
  printf '%s\n' '{"status": "pass", "findings_count": 0, "summary": "gitleaks hook configured in .pre-commit-config.yaml"}'
  exit 0
else
  printf '%s\n' '{"status": "fail", "findings_count": 1, "summary": ".pre-commit-config.yaml present but no gitleaks hook entry"}'
  exit 1
fi
```

```bash
chmod +x profiles/universal/domains/security/controls/gitleaks-precommit/check.sh
```

- [ ] **Step 3: Create instruct.md**

```markdown
# Why gitleaks pre-commit hook

`.gitignore` and "no .env in tree" defend against accidental staging.
gitleaks defends against everything else: hardcoded API keys in source,
PEM blocks pasted into comments, base64 tokens accidentally committed.

It runs in <1s as a pre-commit hook, blocks the commit on detection,
and prints exactly what was found.

## How to add

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

Then: `pre-commit install` to wire the hook.

## Override

Repos that have no commits with possible secrets and use a different
secret-scanning tool (e.g., a CI-only scan) may declare an override.
```

- [ ] **Step 4: Pass fixture**

`fixtures/profiles/universal/domains/security/controls/gitleaks-precommit/pass/.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

- [ ] **Step 5: Fail fixture**

`fixtures/profiles/universal/domains/security/controls/gitleaks-precommit/fail/.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
```

- [ ] **Step 6: Run pytest**

```bash
uv run pytest -v
```

Expected: 65 tests pass.

- [ ] **Step 7: Commit**

```bash
git add profiles/universal/domains/security/controls/gitleaks-precommit/ \
        fixtures/profiles/universal/domains/security/controls/gitleaks-precommit/
git commit -m "feat: universal.security.gitleaks-precommit control"
git push
```

---

## Task 9: universal.vcs.gitignore-present

**Files (new):**
- `profiles/universal/domains/vcs/controls/gitignore-present/{prescribed.yaml,check.sh,instruct.md}`
- `fixtures/.../{pass,fail}/`

- [ ] **Step 1: prescribed.yaml**

```yaml
id: universal.vcs.gitignore-present
version: 1
what: |
  Project has a .gitignore at the repository root.
why: |
  Without .gitignore, developers and agents track build artifacts, IDE state,
  virtual environments, and (worst) secrets. .gitignore is the foundation
  every other VCS-hygiene control assumes.
applies_to:
  - any
```

- [ ] **Step 2: check.sh**

```sh
#!/bin/sh
if [ -f .gitignore ]; then
  printf '%s\n' '{"status": "pass", "findings_count": 0, "summary": ".gitignore present"}'
  exit 0
else
  printf '%s\n' '{"status": "fail", "findings_count": 1, "summary": ".gitignore missing at project root"}'
  exit 1
fi
```

```bash
chmod +x profiles/universal/domains/vcs/controls/gitignore-present/check.sh
```

- [ ] **Step 3: instruct.md**

```markdown
# Why .gitignore

A `.gitignore` is the single most important file for keeping a repository
clean. Without it: build artifacts pollute commits, IDE/.DS_Store noise
appears in diffs, virtual environments get tracked, and the chance of
secret leakage rises sharply.

Generate a starter from https://github.com/github/gitignore for your
language/stack, then augment with project-specific patterns.

## When to override

Never. Every Git project should have a .gitignore.
```

- [ ] **Step 4: Pass fixture**

`fixtures/profiles/universal/domains/vcs/controls/gitignore-present/pass/.gitignore`:
```
.venv/
__pycache__/
```

- [ ] **Step 5: Fail fixture**

`fixtures/profiles/universal/domains/vcs/controls/gitignore-present/fail/README.md`:
```markdown
# Fail fixture — no .gitignore present
```

- [ ] **Step 6: Run pytest, commit**

```bash
uv run pytest -v
git add profiles/universal/domains/vcs/controls/gitignore-present/ \
        fixtures/profiles/universal/domains/vcs/controls/gitignore-present/
git commit -m "feat: universal.vcs.gitignore-present control"
git push
```

Expected: 70 tests pass.

---

## Task 10: universal.vcs.license-present

**Files (new):**
- `profiles/universal/domains/vcs/controls/license-present/{prescribed.yaml,check.sh,instruct.md}`
- `fixtures/.../{pass,fail}/`

- [ ] **Step 1: prescribed.yaml**

```yaml
id: universal.vcs.license-present
version: 1
what: |
  Project has a LICENSE (or LICENSE.md / LICENSE.txt) file at the repository root.
why: |
  Code without a license is "all rights reserved" by default — collaborators,
  contributors, and downstream users cannot legally use it. For open source
  projects, a missing LICENSE blocks adoption. For internal projects, an
  explicit LICENSE (even "Proprietary") prevents legal ambiguity.
applies_to:
  - any
```

- [ ] **Step 2: check.sh**

```sh
#!/bin/sh
for candidate in LICENSE LICENSE.md LICENSE.txt LICENSE.rst COPYING; do
  if [ -f "$candidate" ]; then
    printf '%s\n' '{"status": "pass", "findings_count": 0, "summary": "LICENSE present at project root"}'
    exit 0
  fi
done
printf '%s\n' '{"status": "fail", "findings_count": 1, "summary": "no LICENSE file at project root"}'
exit 1
```

```bash
chmod +x profiles/universal/domains/vcs/controls/license-present/check.sh
```

- [ ] **Step 3: instruct.md**

```markdown
# Why a LICENSE file

Code with no license file is by default "all rights reserved." Even if
your repo is on a public GitHub org, no one — including future-you's
employer, contributors, and dependents — has the legal right to use it.

For open source: pick MIT (most permissive), Apache-2.0 (permissive +
patent grant), or AGPL (strong copyleft). https://choosealicense.com.

For internal/closed source: a single LICENSE file containing
"Proprietary, all rights reserved. © {year} {org}." is sufficient and
removes ambiguity.

## When to override

Personal scratch repos that you genuinely will never share may skip
this. Anything else: pick a license.
```

- [ ] **Step 4: Pass fixture**

`fixtures/profiles/universal/domains/vcs/controls/license-present/pass/LICENSE`:
```
MIT License — fixture
```

- [ ] **Step 5: Fail fixture**

`fixtures/profiles/universal/domains/vcs/controls/license-present/fail/README.md`:
```markdown
# Fail fixture — no LICENSE
```

- [ ] **Step 6: Run pytest, commit**

```bash
uv run pytest -v
git add profiles/universal/domains/vcs/controls/license-present/ \
        fixtures/profiles/universal/domains/vcs/controls/license-present/
git commit -m "feat: universal.vcs.license-present control"
git push
```

Expected: 75 tests pass. **Pause point:** all universal controls (8) shipped.

---

## Task 11: python.quality.ruff-config (Rego port)

**Files (new):**
- `profiles/python/domains/quality/controls/ruff-config/{prescribed.yaml,check.sh,instruct.md,policy.rego,policy_test.rego}`
- `fixtures/profiles/python/domains/quality/controls/ruff-config/{pass,fail}/pyproject.toml`

Source: `agent-harness/src/agent_harness/policies/python/ruff.rego` (verbatim port with package rename).

- [ ] **Step 1: prescribed.yaml**

```yaml
id: python.quality.ruff-config
version: 1
what: |
  pyproject.toml's [tool.ruff] block sets output-format=concise, line-length>=120,
  and an mccabe max-complexity bound.
why: |
  Concise output keeps agent context windows clean. Adequate line length
  prevents constant cosmetic re-wrapping. Complexity limits force
  decomposition into testable units instead of sprawling functions.
applies_to:
  - python
install:
  macos: brew install conftest
  linux: see https://www.conftest.dev/install/
```

- [ ] **Step 2: policy.rego (verbatim port from agent-harness, package renamed)**

```rego
package python.quality.ruff_config

# WHAT: Enforces critical ruff settings: concise output, adequate line length,
# and complexity limits.
# WHY: see instruct.md.
# Input: parsed pyproject.toml (TOML -> JSON via conftest)

import rego.v1

# ── Policy: output-format must be "concise" ──

deny contains msg if {
	ruff := input.tool.ruff
	not ruff["output-format"]
	msg := "ruff: missing 'output-format' — set to \"concise\" for agent-readable one-line errors"
}

deny contains msg if {
	ruff := input.tool.ruff
	ruff["output-format"] != "concise"
	msg := sprintf("ruff: output-format is \"%s\" — should be \"concise\" for agent-readable one-line errors", [ruff["output-format"]])
}

# ── Policy: line-length >= 120 ──

deny contains msg if {
	ruff := input.tool.ruff
	not ruff["line-length"]
	msg := "ruff: missing 'line-length' — set to 120 to reduce unnecessary wrapping noise"
}

deny contains msg if {
	ruff := input.tool.ruff
	ruff["line-length"] < 120
	msg := sprintf("ruff: line-length is %d — should be >= 120 to reduce unnecessary wrapping noise for agents", [ruff["line-length"]])
}

# ── Policy: complexity limits set ──

deny contains msg if {
	ruff := input.tool.ruff
	not ruff.lint.mccabe["max-complexity"]
	msg := "ruff: missing mccabe max-complexity — set to 10 to prevent agents from generating sprawling functions"
}

deny contains msg if {
	ruff := input.tool.ruff
	ruff.lint.mccabe["max-complexity"] > 15
	msg := sprintf("ruff: mccabe max-complexity is %d — should be <= 15 (recommended: 10)", [ruff.lint.mccabe["max-complexity"]])
}
```

- [ ] **Step 3: policy_test.rego (port)**

```rego
package python.quality.ruff_config_test

import rego.v1
import data.python.quality.ruff_config

test_missing_output_format_fires if {
	ruff_config.deny with input as {"tool": {"ruff": {"line-length": 140, "lint": {"mccabe": {"max-complexity": 10}}}}}
}

test_wrong_output_format_fires if {
	ruff_config.deny with input as {"tool": {"ruff": {"output-format": "full", "line-length": 140, "lint": {"mccabe": {"max-complexity": 10}}}}}
}

test_missing_line_length_fires if {
	ruff_config.deny with input as {"tool": {"ruff": {"output-format": "concise", "lint": {"mccabe": {"max-complexity": 10}}}}}
}

test_short_line_length_fires if {
	ruff_config.deny with input as {"tool": {"ruff": {"output-format": "concise", "line-length": 80, "lint": {"mccabe": {"max-complexity": 10}}}}}
}

test_missing_complexity_fires if {
	ruff_config.deny with input as {"tool": {"ruff": {"output-format": "concise", "line-length": 140, "lint": {}}}}
}

test_high_complexity_fires if {
	ruff_config.deny with input as {"tool": {"ruff": {"output-format": "concise", "line-length": 140, "lint": {"mccabe": {"max-complexity": 20}}}}}
}

test_good_config_passes if {
	count(ruff_config.deny) == 0 with input as {"tool": {"ruff": {"output-format": "concise", "line-length": 140, "lint": {"mccabe": {"max-complexity": 10}}}}}
}
```

- [ ] **Step 4: check.sh**

```sh
#!/bin/sh
exec sh "$AGENT_WEISS_BUNDLE/scripts/run_rego_check.sh" \
  "pyproject.toml" \
  "profiles/python/domains/quality/controls/ruff-config/policy.rego"
```

```bash
chmod +x profiles/python/domains/quality/controls/ruff-config/check.sh
```

- [ ] **Step 5: instruct.md**

```markdown
# Why ruff-config matters for agents

`ruff` is the de facto Python linter. The default config is fine for
humans but suboptimal for AI agents:

- **`output-format = "concise"`** is the #1 knob. Without it, agents see
  5-line context blocks per lint error; with it, one line. This dominates
  context-window cost on lint-heavy diffs.

- **`line-length >= 120`** prevents agents from constantly re-wrapping
  lines that read fine. The default 88 was set for `black`'s aesthetic;
  it's a poor target for agents.

- **`mccabe max-complexity` set** forces decomposition. Without it,
  agents happily generate 200-line functions with deep nesting because
  no signal stops them.

## How to fix

Add to `pyproject.toml`:

```toml
[tool.ruff]
output-format = "concise"
line-length = 120

[tool.ruff.lint.mccabe]
max-complexity = 10
```

## Override

Teams with strong style preferences (line-length 88, etc.) may override.
Document the trade-off: "we accept noisier diffs in exchange for visual
density."
```

- [ ] **Step 6: pass fixture**

`fixtures/profiles/python/domains/quality/controls/ruff-config/pass/pyproject.toml`:
```toml
[project]
name = "fixture"
version = "0.1.0"

[tool.ruff]
output-format = "concise"
line-length = 140

[tool.ruff.lint.mccabe]
max-complexity = 10
```

- [ ] **Step 7: fail fixture**

`fixtures/profiles/python/domains/quality/controls/ruff-config/fail/pyproject.toml`:
```toml
[project]
name = "fixture"
version = "0.1.0"

[tool.ruff]
output-format = "full"
line-length = 80
```

- [ ] **Step 8: Run pytest + conftest verify**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest -v
conftest verify --policy profiles/python/domains/quality/controls/ruff-config/policy.rego
```

Expected: 80 tests pass; 7 Rego unit tests pass.

- [ ] **Step 9: Commit**

```bash
git add profiles/python/domains/quality/controls/ruff-config/ \
        fixtures/profiles/python/domains/quality/controls/ruff-config/
git commit -m "feat: python.quality.ruff-config (Rego port from agent-harness)"
git push
```

---

## Task 12: python.quality.ty-config (new)

**Files (new):**
- `profiles/python/domains/quality/controls/ty-config/{prescribed.yaml,check.sh,instruct.md}`
- `fixtures/.../{pass,fail}/pyproject.toml`

`ty` is Astral's new type checker. Plan 2 ships a minimal control: `[tool.ty]` block exists with at least one configured key. Shell-only check (Rego port can come later).

- [ ] **Step 1: prescribed.yaml**

```yaml
id: python.quality.ty-config
version: 1
what: |
  pyproject.toml has a [tool.ty] section with at least one configured key.
why: |
  Type checking gives agents structural feedback they can't get from runtime
  errors. ty (Astral) is fast enough to run on every save and surfaces
  type misuse before tests do. A bare [tool.ty] section is the minimum signal
  that the project takes type-checking seriously.
applies_to:
  - python
```

- [ ] **Step 2: check.sh**

```sh
#!/bin/sh
# python.quality.ty-config — verify [tool.ty] block exists in pyproject.toml.
if [ ! -f pyproject.toml ]; then
  printf '%s\n' '{"status": "pass", "findings_count": 0, "summary": "pyproject.toml not present — control not applicable"}'
  exit 0
fi
if grep -q '^\[tool\.ty\]' pyproject.toml; then
  printf '%s\n' '{"status": "pass", "findings_count": 0, "summary": "[tool.ty] section configured"}'
  exit 0
else
  printf '%s\n' '{"status": "fail", "findings_count": 1, "summary": "pyproject.toml has no [tool.ty] section"}'
  exit 1
fi
```

```bash
chmod +x profiles/python/domains/quality/controls/ty-config/check.sh
```

- [ ] **Step 3: instruct.md**

```markdown
# Why type-check with ty

Type checking catches a class of bug that tests miss: structural misuse
(passing `int` where `Path` is expected, calling a method that doesn't
exist on a type). For agents, types are also a guidance signal —
LSP-aware tools surface them inline.

`ty` (Astral) is the new generation: fast enough for save-on-keystroke
type checking, with a config-light defaults model.

## How to add

Minimal:
```toml
[tool.ty]
# accept defaults; checks all of src/
```

Recommended:
```toml
[tool.ty]
include = ["src", "tests"]
```

Then: `uv run ty check`.

## Override

Projects already using mypy or pyright may declare an override referencing
the existing type checker. Don't run two checkers — pick one.
```

- [ ] **Step 4: pass fixture**

`fixtures/profiles/python/domains/quality/controls/ty-config/pass/pyproject.toml`:
```toml
[project]
name = "fixture"
version = "0.1.0"

[tool.ty]
include = ["src"]
```

- [ ] **Step 5: fail fixture**

`fixtures/profiles/python/domains/quality/controls/ty-config/fail/pyproject.toml`:
```toml
[project]
name = "fixture"
version = "0.1.0"
```

- [ ] **Step 6: Run pytest, commit**

```bash
uv run pytest -v
git add profiles/python/domains/quality/controls/ty-config/ \
        fixtures/profiles/python/domains/quality/controls/ty-config/
git commit -m "feat: python.quality.ty-config control"
git push
```

Expected: 85 tests pass.

---

## Task 13: python.testing.pytest-config (Rego port)

**Files (new):**
- `profiles/python/domains/testing/controls/pytest-config/{prescribed.yaml,check.sh,instruct.md,policy.rego,policy_test.rego}`
- `fixtures/.../{pass,fail}/pyproject.toml`

Source: `agent-harness/src/agent_harness/policies/python/pytest.rego` — covers strict-markers, --cov, and --cov-fail-under threshold (≥30). Verbatim port with package rename.

- [ ] **Step 1: prescribed.yaml**

```yaml
id: python.testing.pytest-config
version: 1
what: |
  pyproject.toml's [tool.pytest.ini_options] addopts includes --strict-markers,
  --cov, and --cov-fail-under with a threshold ≥ 30.
why: |
  --strict-markers prevents silent typos in marker names. --cov runs coverage
  on every test invocation. --cov-fail-under gates merges on coverage
  regression. Below 30%, the threshold catches nothing meaningful.
applies_to:
  - python
install:
  macos: brew install conftest
```

- [ ] **Step 2: policy.rego (port)**

`profiles/python/domains/testing/controls/pytest-config/policy.rego`:
```rego
package python.testing.pytest_config

# WHAT: Ensures pytest is configured with strict markers, coverage, and a
# meaningful coverage threshold.
# WHY: see instruct.md.
# Input: parsed pyproject.toml (TOML -> JSON via conftest)

import rego.v1

# ── deny: strict-markers must be enabled ──

deny contains msg if {
	opts := input.tool.pytest.ini_options
	addopts := opts.addopts
	not contains(addopts, "--strict-markers")
	msg := "pytest: addopts missing '--strict-markers' — catches marker typos deterministically"
}

# ── deny: coverage must be enabled ──

deny contains msg if {
	opts := input.tool.pytest.ini_options
	addopts := opts.addopts
	not contains(addopts, "--cov")
	msg := "pytest: addopts missing '--cov' — coverage should run with every test invocation"
}

# ── deny: coverage threshold must exist ──

deny contains msg if {
	opts := input.tool.pytest.ini_options
	addopts := opts.addopts
	not contains(addopts, "--cov-fail-under")
	msg := "pytest: addopts missing '--cov-fail-under' — set a coverage threshold (recommended: 95)"
}

# ── deny: coverage threshold must not be absurdly low ──
# Below 30% is not a gate — it catches nothing meaningful.

deny contains msg if {
	opts := input.tool.pytest.ini_options
	addopts := opts.addopts
	contains(addopts, "--cov-fail-under")
	parts := split(addopts, "--cov-fail-under=")
	count(parts) > 1
	threshold_str := split(parts[1], " ")[0]
	threshold := to_number(threshold_str)
	threshold < 30
	msg := sprintf("pytest: --cov-fail-under=%v is below 30%% — this gate catches nothing meaningful", [threshold])
}
```

- [ ] **Step 3: policy_test.rego (port)**

`profiles/python/domains/testing/controls/pytest-config/policy_test.rego`:
```rego
package python.testing.pytest_config_test

import rego.v1
import data.python.testing.pytest_config

test_missing_strict_markers_fires if {
	pytest_config.deny with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v --cov --cov-fail-under=95"}}}}
}

test_missing_cov_fires if {
	pytest_config.deny with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v --strict-markers --cov-fail-under=95"}}}}
}

test_missing_cov_fail_under_fires if {
	pytest_config.deny with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v --strict-markers --cov"}}}}
}

test_threshold_below_30_fires if {
	pytest_config.deny with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v --strict-markers --cov --cov-fail-under=15"}}}}
}

test_threshold_at_30_passes if {
	count(pytest_config.deny) == 0 with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v --strict-markers --cov --cov-fail-under=30"}}}}
}

test_good_config_passes if {
	count(pytest_config.deny) == 0 with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v --strict-markers --cov --cov-fail-under=95"}}}}
}
```

- [ ] **Step 4: check.sh**

```sh
#!/bin/sh
exec sh "$AGENT_WEISS_BUNDLE/scripts/run_rego_check.sh" \
  "pyproject.toml" \
  "profiles/python/domains/testing/controls/pytest-config/policy.rego"
```

```bash
chmod +x profiles/python/domains/testing/controls/pytest-config/check.sh
```

- [ ] **Step 5: instruct.md**

```markdown
# Why pytest-config

`--strict-markers` prevents silent typos — `@pytest.mark.slo` (typo of `slow`)
silently runs zero tests; the gap shows up only when CI is suspiciously fast.

`--cov` runs coverage on every test invocation. `--cov-fail-under=N` gates
merges on coverage regression. The threshold can start low (30 is the
minimum we accept) and trend up. Below 30 it catches nothing meaningful.

## How to fix

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "-v --strict-markers --cov=src --cov-fail-under=30"
```

Tighten `--cov-fail-under` over time as the test suite matures.

## Override

Codebases with non-runtime modules (pure type stubs, generated SDKs) may
legitimately skip coverage. Declare an override.
```

- [ ] **Step 6: pass + fail fixtures**

Pass `fixtures/profiles/python/domains/testing/controls/pytest-config/pass/pyproject.toml`:
```toml
[project]
name = "fixture"
version = "0.1.0"

[tool.pytest.ini_options]
addopts = "-v --strict-markers --cov=src --cov-fail-under=95"
```

Fail `fixtures/profiles/python/domains/testing/controls/pytest-config/fail/pyproject.toml`:
```toml
[project]
name = "fixture"
version = "0.1.0"

[tool.pytest.ini_options]
addopts = "-v"
```

- [ ] **Step 7: Run pytest + conftest verify, commit**

```bash
uv run pytest -v
conftest verify --policy profiles/python/domains/testing/controls/pytest-config/policy.rego
git add profiles/python/domains/testing/controls/pytest-config/ \
        fixtures/profiles/python/domains/testing/controls/pytest-config/
git commit -m "feat: python.testing.pytest-config (Rego port from agent-harness)"
git push
```

Expected: 90 tests pass; 6 Rego unit tests pass.

---

## Task 14: python.testing.coverage-config (Rego port)

**Files (new):**
- `profiles/python/domains/testing/controls/coverage-config/{prescribed.yaml,check.sh,instruct.md,policy.rego,policy_test.rego}`
- `fixtures/.../{pass,fail}/pyproject.toml`

Source: `agent-harness/src/agent_harness/policies/python/coverage.rego` — covers the `[tool.coverage]` block (skip_covered + branch). The `--cov-fail-under` threshold is handled by Task 13 (pytest-config); this control covers the remaining `[tool.coverage]` config hygiene.

> **Note:** the original plan title used "coverage-threshold". Renamed to "coverage-config" to match the source policy's actual scope (it's about the `[tool.coverage]` section, not the threshold which lives in pytest's addopts).

- [ ] **Step 1: prescribed.yaml**

```yaml
id: python.testing.coverage-config
version: 1
what: |
  pyproject.toml's [tool.coverage] section sets report.skip_covered=true and
  run.branch=true.
why: |
  Without skip_covered=true, agents see 50+ fully-covered files drowning the
  2 that need work. Branch coverage catches untested if/else branches that
  line-only coverage misses.
applies_to:
  - python
install:
  macos: brew install conftest
```

- [ ] **Step 2: policy.rego (port)**

`profiles/python/domains/testing/controls/coverage-config/policy.rego`:
```rego
package python.testing.coverage_config

# WHAT: Ensures [tool.coverage] is configured for agent-readable output.
# WHY: see instruct.md.
# Input: parsed pyproject.toml (TOML -> JSON via conftest)

import rego.v1

# ── Policy: skip_covered = true ──

deny contains msg if {
	report := input.tool.coverage.report
	not report.skip_covered
	msg := "coverage.report: missing 'skip_covered' — set to true so agents only see files with gaps"
}

deny contains msg if {
	report := input.tool.coverage.report
	report.skip_covered == false
	msg := "coverage.report: skip_covered is false — set to true so agents only see files with gaps"
}

# ── Policy: branch coverage enabled ──

deny contains msg if {
	run := input.tool.coverage.run
	not run.branch
	msg := "coverage.run: missing 'branch' — set to true to catch untested if/else branches"
}

deny contains msg if {
	run := input.tool.coverage.run
	run.branch == false
	msg := "coverage.run: branch is false — set to true to catch untested if/else branches"
}
```

- [ ] **Step 3: policy_test.rego (port)**

`profiles/python/domains/testing/controls/coverage-config/policy_test.rego`:
```rego
package python.testing.coverage_config_test

import rego.v1
import data.python.testing.coverage_config

test_missing_skip_covered_fires if {
	coverage_config.deny with input as {"tool": {"coverage": {
		"report": {},
		"run": {"branch": true},
	}}}
}

test_skip_covered_false_fires if {
	coverage_config.deny with input as {"tool": {"coverage": {
		"report": {"skip_covered": false},
		"run": {"branch": true},
	}}}
}

test_missing_branch_fires if {
	coverage_config.deny with input as {"tool": {"coverage": {
		"report": {"skip_covered": true},
		"run": {},
	}}}
}

test_branch_false_fires if {
	coverage_config.deny with input as {"tool": {"coverage": {
		"report": {"skip_covered": true},
		"run": {"branch": false},
	}}}
}

test_good_config_passes if {
	count(coverage_config.deny) == 0 with input as {"tool": {"coverage": {
		"report": {"skip_covered": true},
		"run": {"branch": true},
	}}}
}
```

- [ ] **Step 4: check.sh**

```sh
#!/bin/sh
exec sh "$AGENT_WEISS_BUNDLE/scripts/run_rego_check.sh" \
  "pyproject.toml" \
  "profiles/python/domains/testing/controls/coverage-config/policy.rego"
```

```bash
chmod +x profiles/python/domains/testing/controls/coverage-config/check.sh
```

- [ ] **Step 5: instruct.md**

```markdown
# Why coverage config matters for agents

Coverage tooling defaults are tuned for humans reading HTML reports, not
agents reading terminal output:

- **`report.skip_covered = true`** is critical. Without it, an agent sees
  50+ fully-covered files in the output, drowning the 2 that actually
  need work. With it, the agent only sees the gaps.
- **`run.branch = true`** enables branch coverage (in addition to line
  coverage). Without branch, an `if cond:` with a tested body and untested
  else looks "covered" — but the else branch is dead.

## How to fix

```toml
[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
skip_covered = true
```

## Override

Codebases with no test runtime can override.
```

- [ ] **Step 6: pass + fail fixtures**

Pass `fixtures/profiles/python/domains/testing/controls/coverage-config/pass/pyproject.toml`:
```toml
[project]
name = "fixture"
version = "0.1.0"

[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
skip_covered = true
```

Fail `fixtures/profiles/python/domains/testing/controls/coverage-config/fail/pyproject.toml`:
```toml
[project]
name = "fixture"
version = "0.1.0"

[tool.coverage.run]
source = ["src"]

[tool.coverage.report]
```

- [ ] **Step 7: Run pytest + conftest verify, commit**

```bash
uv run pytest -v
conftest verify --policy profiles/python/domains/testing/controls/coverage-config/policy.rego
git add profiles/python/domains/testing/controls/coverage-config/ \
        fixtures/profiles/python/domains/testing/controls/coverage-config/
git commit -m "feat: python.testing.coverage-config (Rego port from agent-harness)"
git push
```

Expected: 95 tests pass; 5 Rego unit tests pass.

---

## Task 15: python.testing.test-isolation (Rego port)

**Files (new):**
- `profiles/python/domains/testing/controls/test-isolation/{prescribed.yaml,check.sh,instruct.md,policy.rego,policy_test.rego}`
- `fixtures/.../{pass,fail}/pyproject.toml`

Source: `agent-harness/src/agent_harness/policies/python/test_isolation.rego`. The source's deny rule fires when `[tool.pytest.ini_options]` lacks an `env` key (pytest-env config) — without it, tests run against whatever `DATABASE_URL` is in the developer's shell, including production.

- [ ] **Step 1: prescribed.yaml**

```yaml
id: python.testing.test-isolation
version: 1
what: |
  pyproject.toml's [tool.pytest.ini_options] declares an `env` key with
  test-isolated environment values (DATABASE_URL pointing to a test DB,
  REDIS_URL on a test port, etc.).
why: |
  Without pytest-env injecting test environment values, tests inherit
  whatever DATABASE_URL is in the developer's shell. On a dev machine
  pointed at production, `make test` corrupts production data with no
  warning. The `env` key in pytest config (read by pytest-env) injects
  test-specific values BEFORE pydantic-settings or similar code reads them.
applies_to:
  - python
install:
  macos: brew install conftest
```

- [ ] **Step 2: policy.rego (port)**

`profiles/python/domains/testing/controls/test-isolation/policy.rego`:
```rego
package python.testing.test_isolation

# WHAT: Ensures pytest-env config injects test environment variables before
# the application reads them.
# WHY: see instruct.md.
# Input: parsed pyproject.toml (TOML -> JSON via conftest)

import rego.v1

# ── Policy: pytest-env configured ──

deny contains msg if {
	opts := input.tool.pytest.ini_options
	not opts.env
	msg := "pytest: no 'env' configuration — add pytest-env entries to isolate tests from production (e.g., test database URL on a separate port)"
}
```

- [ ] **Step 3: policy_test.rego (port)**

`profiles/python/domains/testing/controls/test-isolation/policy_test.rego`:
```rego
package python.testing.test_isolation_test

import rego.v1
import data.python.testing.test_isolation

test_missing_env_fires if {
	test_isolation.deny with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v"}}}}
}

test_with_env_passes if {
	count(test_isolation.deny) == 0 with input as {"tool": {"pytest": {"ini_options": {
		"addopts": "-v",
		"env": ["DATABASE_URL=postgresql://localhost:5433/test_db"],
	}}}}
}
```

- [ ] **Step 4: check.sh**

```sh
#!/bin/sh
exec sh "$AGENT_WEISS_BUNDLE/scripts/run_rego_check.sh" \
  "pyproject.toml" \
  "profiles/python/domains/testing/controls/test-isolation/policy.rego"
```

```bash
chmod +x profiles/python/domains/testing/controls/test-isolation/check.sh
```

- [ ] **Step 5: instruct.md**

```markdown
# Why test isolation matters

The catastrophic story: agent runs `make test` on a developer machine.
The shell has `DATABASE_URL=postgresql://localhost:5432/prod` from the
last debug session. Tests connect to prod, run their setup/teardown,
and corrupt or delete real data. No warning, no error — the tests pass.

`pytest-env` plus an `env` block in `[tool.pytest.ini_options]` injects
test-specific environment values BEFORE the application code (pydantic
settings, env-reading config loaders) sees them. Even if the shell has
production URLs, the test DB URL wins.

## How to fix

Install pytest-env:
```toml
[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-env>=1",
]
```

Add an `env` block:
```toml
[tool.pytest.ini_options]
addopts = "-v --strict-markers"
env = [
    "DATABASE_URL=postgresql://localhost:5433/test_db",
    "REDIS_URL=redis://localhost:6380/0",
]
```

Use a separate port for the test DB (5433 instead of 5432) so even a
misconfigured local Postgres can't accidentally hit prod.

## Override

Pure-unit-test codebases with no env-reading code (no DB, no external
services, no settings loader) may legitimately have no `env` block.
Declare an override.
```

- [ ] **Step 6: pass + fail fixtures**

Pass `fixtures/profiles/python/domains/testing/controls/test-isolation/pass/pyproject.toml`:
```toml
[project]
name = "fixture"
version = "0.1.0"

[tool.pytest.ini_options]
addopts = "-v --strict-markers"
env = [
  "DATABASE_URL=postgresql://localhost:5433/test_db",
]
```

Fail `fixtures/profiles/python/domains/testing/controls/test-isolation/fail/pyproject.toml`:
```toml
[project]
name = "fixture"
version = "0.1.0"

[tool.pytest.ini_options]
addopts = "-v --strict-markers"
```

- [ ] **Step 7: Run pytest + conftest verify, commit**

```bash
uv run pytest -v
conftest verify --policy profiles/python/domains/testing/controls/test-isolation/policy.rego
git add profiles/python/domains/testing/controls/test-isolation/ \
        fixtures/profiles/python/domains/testing/controls/test-isolation/
git commit -m "feat: python.testing.test-isolation (Rego port from agent-harness)"
git push
```

Expected: 100 tests pass; 2 Rego unit tests pass. **Pause point:** all python controls (5) shipped.

---

## Task 16: typescript.project-structure.package-json (Rego port)

**Files (new):**
- `profiles/typescript/domains/project-structure/controls/package-json/{prescribed.yaml,check.sh,instruct.md,policy.rego,policy_test.rego}`
- `fixtures/.../{pass,fail}/package.json`

Source: `agent-harness/src/agent_harness/policies/javascript/package.rego`. Source uses both `deny` (engines, wildcard versions) and `warn` (missing/wrong `type`). Plan 1's contract parser only models pass/fail/setup-unmet — no warning level. **Decision:** convert source `warn` rules into `deny` rules so the type-must-be-module check actually gates. (If you want a "soft" type rule later, add a `lenient` profile variant.)

- [ ] **Step 1: prescribed.yaml**

```yaml
id: typescript.project-structure.package-json
version: 1
what: |
  package.json declares "type": "module", an engines field (engines.node), and
  no wildcard ("*") version ranges in dependencies or devDependencies.
why: |
  ESM ("type": "module") is the modern default — without it Node treats .js as
  CJS and modern import syntax breaks. engines.node prevents silent breakage
  on developer machines with too-old Node. Wildcard versions accept any
  release including breaking majors, making npm install non-deterministic.
applies_to:
  - typescript
install:
  macos: brew install conftest
```

- [ ] **Step 2: policy.rego (port)**

`profiles/typescript/domains/project-structure/controls/package-json/policy.rego`:
```rego
package typescript.project_structure.package_json

# WHAT: Ensures package.json has engines, type:"module", and no wildcard versions.
# WHY: see instruct.md.
# Input: parsed package.json (JSON)

import rego.v1

# ── Policy: engines field must exist ──

deny contains msg if {
	not input.engines
	msg := "package.json: missing 'engines' field — specify Node version to prevent version mismatch"
}

# ── Policy: type must be "module" ──
# Source policy used `warn`; converted to `deny` because agent-weiss contract
# has no warn level (and modern TS projects should be ESM by default).

deny contains msg if {
	not input.type
	msg := "package.json: missing 'type' field — set '\"type\": \"module\"' for explicit ESM"
}

deny contains msg if {
	input.type
	input.type != "module"
	msg := sprintf("package.json: 'type' is '%s' — should be 'module' for ESM consistency", [input.type])
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

- [ ] **Step 3: policy_test.rego (port)**

`profiles/typescript/domains/project-structure/controls/package-json/policy_test.rego`:
```rego
package typescript.project_structure.package_json_test

import rego.v1
import data.typescript.project_structure.package_json

test_missing_engines_denied if {
	count(package_json.deny) > 0 with input as {"name": "x", "version": "1.0.0", "type": "module"}
}

test_engines_present_passes if {
	count(package_json.deny) == 0 with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"type": "module",
	}
}

test_missing_type_denied if {
	count(package_json.deny) > 0 with input as {
		"name": "x",
		"engines": {"node": ">=22"},
	}
}

test_type_module_no_deny if {
	count(package_json.deny) == 0 with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"type": "module",
	}
}

test_wildcard_dep_denied if {
	count(package_json.deny) > 0 with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"type": "module",
		"dependencies": {"bad-pkg": "*"},
	}
}

test_pinned_dep_passes if {
	count(package_json.deny) == 0 with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"type": "module",
		"dependencies": {"good-pkg": "^1.2.3"},
	}
}

test_wildcard_devdep_denied if {
	count(package_json.deny) > 0 with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"type": "module",
		"devDependencies": {"bad-dev": "*"},
	}
}
```

- [ ] **Step 4: check.sh**

```sh
#!/bin/sh
exec sh "$AGENT_WEISS_BUNDLE/scripts/run_rego_check.sh" \
  "package.json" \
  "profiles/typescript/domains/project-structure/controls/package-json/policy.rego"
```

```bash
chmod +x profiles/typescript/domains/project-structure/controls/package-json/check.sh
```

- [ ] **Step 5: instruct.md**

```markdown
# Why package.json conventions matter

A well-formed `package.json` is the project's machine-readable spec.

- **`"type": "module"`** declares ESM. Without it, Node treats `.js` as
  CJS, breaking modern `import` syntax silently or noisily depending on
  context. (Modern TS projects should always be ESM.)
- **`engines.node`** locks the minimum Node version. Without it, a
  developer or CI on an old Node sees mysterious runtime errors instead
  of a clean "your Node is too old."
- **No wildcard versions (`"*"`)** in dependencies. Wildcards accept
  anything, including breaking majors. `npm install` returns different
  versions each time, making bugs non-reproducible.

## How to fix

```json
{
  "name": "my-project",
  "type": "module",
  "engines": { "node": ">=22" },
  "dependencies": {
    "some-lib": "^1.2.3"
  }
}
```

## Override

Pure-CJS legacy packages (rare in 2026) may override the `"type": "module"`
rule with a documented reason. Wildcard versions never have a legitimate
override — pin them.
```

- [ ] **Step 6: pass + fail fixtures**

Pass `fixtures/profiles/typescript/domains/project-structure/controls/package-json/pass/package.json`:
```json
{
  "name": "fixture",
  "version": "0.1.0",
  "type": "module",
  "engines": { "node": ">=22" },
  "dependencies": {
    "some-lib": "^1.2.3"
  }
}
```

Fail `fixtures/profiles/typescript/domains/project-structure/controls/package-json/fail/package.json`:
```json
{
  "name": "fixture",
  "version": "0.1.0",
  "dependencies": {
    "bad-pkg": "*"
  }
}
```

- [ ] **Step 7: Run pytest + conftest verify, commit**

```bash
uv run pytest -v
conftest verify --policy profiles/typescript/domains/project-structure/controls/package-json/policy.rego
git add profiles/typescript/domains/project-structure/controls/package-json/ \
        fixtures/profiles/typescript/domains/project-structure/controls/package-json/
git commit -m "feat: typescript.project-structure.package-json (Rego port from agent-harness)"
git push
```

Expected: 105 tests pass; 7 Rego unit tests pass.

---

## Task 17: typescript.quality.biome-config

**Files (new):**
- `profiles/typescript/domains/quality/controls/biome-config/{prescribed.yaml,check.sh,instruct.md}`
- `fixtures/.../{pass,fail}/`

Shell-only check: `biome.json` (or `biome.jsonc`) exists at repo root with at least one configured rule. Plan 2 keeps it simple — Rego port can come later.

- [ ] **Step 1: prescribed.yaml**

```yaml
id: typescript.quality.biome-config
version: 1
what: |
  Project has biome.json (or biome.jsonc) at the repo root with a configured
  formatter or linter rules.
why: |
  Biome replaces ESLint + Prettier with a single fast Rust-based tool.
  Without configuration, it runs with defaults that aren't tuned for the
  project. Even a near-empty config is the signal that the project takes
  formatting/linting seriously.
applies_to:
  - typescript
```

- [ ] **Step 2: check.sh**

```sh
#!/bin/sh
# typescript.quality.biome-config
for candidate in biome.json biome.jsonc; do
  if [ -f "$candidate" ]; then
    # Sanity-check: file is non-empty and parses as JSON-ish (at least has braces).
    if grep -q '{' "$candidate"; then
      printf '%s\n' '{"status": "pass", "findings_count": 0, "summary": "biome config present"}'
      exit 0
    fi
  fi
done
printf '%s\n' '{"status": "fail", "findings_count": 1, "summary": "no biome.json or biome.jsonc at project root"}'
exit 1
```

```bash
chmod +x profiles/typescript/domains/quality/controls/biome-config/check.sh
```

- [ ] **Step 3: instruct.md**

```markdown
# Why biome

Biome is the fast Rust replacement for ESLint + Prettier. One tool, one
config, sub-second runs even on large codebases.

For agents: a single config file (vs. ESLint's plugin-soup) means less
context to load when the agent needs to understand the project's style.

## How to add

```bash
npm install --save-dev --save-exact @biomejs/biome
npx @biomejs/biome init
```

This creates `biome.json` with sensible defaults. Customize as needed.

## Override

Teams committed to ESLint+Prettier (often for legacy plugin compatibility)
may declare an override referencing their existing config.
```

- [ ] **Step 4-5: fixtures**

Pass `fixtures/.../pass/biome.json`:
```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.0/schema.json",
  "linter": { "enabled": true }
}
```

Fail `fixtures/.../fail/README.md`:
```markdown
# Fail fixture — no biome config
```

- [ ] **Step 6: Run pytest, commit**

```bash
uv run pytest -v
git add profiles/typescript/domains/quality/controls/biome-config/ \
        fixtures/profiles/typescript/domains/quality/controls/biome-config/
git commit -m "feat: typescript.quality.biome-config control"
git push
```

Expected: 110 tests pass.

---

## Task 18: typescript.testing.vitest-config

**Files (new):**
- `profiles/typescript/domains/testing/controls/vitest-config/{prescribed.yaml,check.sh,instruct.md}`
- `fixtures/.../{pass,fail}/`

Shell-only: `vitest.config.{ts,js,mjs}` exists OR `package.json` has a `vitest` config block.

- [ ] **Step 1: prescribed.yaml**

```yaml
id: typescript.testing.vitest-config
version: 1
what: |
  Project has vitest.config.ts (or .js/.mjs) at the repo root, OR package.json
  declares a vitest config block.
why: |
  Vitest is the de facto modern TS test runner — Vite-native, fast HMR-style
  test reruns, ESM-first. Without config, it runs with defaults that may not
  match the project's source/test layout. Explicit config makes test discovery
  predictable for both agents and humans.
applies_to:
  - typescript
```

- [ ] **Step 2: check.sh**

```sh
#!/bin/sh
# typescript.testing.vitest-config
for candidate in vitest.config.ts vitest.config.js vitest.config.mjs; do
  if [ -f "$candidate" ]; then
    printf '%s\n' '{"status": "pass", "findings_count": 0, "summary": "vitest config file present"}'
    exit 0
  fi
done
if [ -f package.json ] && grep -q '"vitest"' package.json; then
  printf '%s\n' '{"status": "pass", "findings_count": 0, "summary": "vitest config in package.json"}'
  exit 0
fi
printf '%s\n' '{"status": "fail", "findings_count": 1, "summary": "no vitest config (file or package.json block)"}'
exit 1
```

```bash
chmod +x profiles/typescript/domains/testing/controls/vitest-config/check.sh
```

- [ ] **Step 3: instruct.md**

```markdown
# Why vitest

Vitest replaces Jest for modern TS projects: native ESM, sub-second cold
starts, identical-API test files, and Vite-driven HMR for test reruns.
For projects already using Vite, Vitest reuses the same config and
plugin chain.

For agents: a Vitest config file is the unambiguous "tests live here, run
them with `npx vitest`" signal.

## How to add

Minimal `vitest.config.ts`:
```ts
import { defineConfig } from 'vitest/config';
export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
  },
});
```

## Override

Projects on Jest, ava, or other runners may declare an override referencing
the existing tool.
```

- [ ] **Step 4: pass + fail fixtures**

Pass `fixtures/.../pass/vitest.config.ts`:
```ts
import { defineConfig } from 'vitest/config';
export default defineConfig({ test: { globals: true } });
```

Fail `fixtures/.../fail/README.md`:
```markdown
# Fail fixture — no vitest config
```

- [ ] **Step 5: Run pytest, commit**

```bash
uv run pytest -v
git add profiles/typescript/domains/testing/controls/vitest-config/ \
        fixtures/profiles/typescript/domains/testing/controls/vitest-config/
git commit -m "feat: typescript.testing.vitest-config control"
git push
```

Expected: 115 tests pass. **Pause point:** all typescript controls (3) shipped — full v1 control library complete.

---

## Task 19: Final verification + Rego unit-test runner

**Files:**
- Create: `tests/test_rego_unit_tests.py`

A self-test that ensures every shipped `policy.rego` has a sibling `policy_test.rego` and the Rego unit tests pass.

- [ ] **Step 1: Write the test**

Create `tests/test_rego_unit_tests.py`:

```python
"""Self-test: every policy.rego has a policy_test.rego and the unit tests pass."""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES = REPO_ROOT / "profiles"


def _all_policies() -> list[Path]:
    return sorted(PROFILES.rglob("policy.rego"))


@pytest.mark.parametrize("policy", _all_policies(), ids=lambda p: str(p.relative_to(PROFILES)))
def test_policy_has_test_sibling(policy: Path):
    """Every policy.rego must ship a policy_test.rego sibling."""
    sibling = policy.with_name("policy_test.rego")
    assert sibling.exists(), f"missing {sibling}"


@pytest.mark.skipif(shutil.which("conftest") is None, reason="conftest not installed")
@pytest.mark.parametrize("policy", _all_policies(), ids=lambda p: str(p.relative_to(PROFILES)))
def test_policy_unit_tests_pass(policy: Path):
    """conftest verify must succeed for every policy.rego."""
    sibling = policy.with_name("policy_test.rego")
    if not sibling.exists():
        pytest.skip("no test sibling")
    proc = subprocess.run(
        ["conftest", "verify", "--policy", str(policy)],
        capture_output=True,
        text=True,
        cwd=policy.parent,
    )
    assert proc.returncode == 0, (
        f"conftest verify failed for {policy.relative_to(PROFILES)}\n"
        f"stdout: {proc.stdout}\n"
        f"stderr: {proc.stderr}"
    )
```

- [ ] **Step 2: Run pytest**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_rego_unit_tests.py -v
```

Expected: 12 tests pass (6 policies × 2 tests = 12; or some skip if conftest missing).

Run full suite:
```bash
uv run pytest -v
```

Expected: 115+12 = 127 tests pass.

- [ ] **Step 3: Commit + verify CI green**

```bash
git add tests/test_rego_unit_tests.py
git commit -m "test: every policy.rego has a passing test sibling"
git push
gh run list --repo yoselabs/agent-weiss --limit 1
gh run watch  # wait for green
```

Expected: CI green.

---

## Task 20: Update roadmap + tag milestone

**Files:**
- Modify: `/Users/iorlas/Workspaces/agent-harness/docs/superpowers/plans/2026-04-14-agent-weiss-roadmap.md`

- [ ] **Step 1: Update roadmap**

Edit the Plan sequence table in the agent-harness roadmap. Change Plan 2's `Status` from `Pending` to `Done`. Add this line to the "v1 control inventory" cross-cutting decisions if it's not already implicit:

```
| v1 controls shipped | 16 (1 from Plan 1 + 15 from Plan 2): see Plan 2's "v1 control inventory after Plan 2" table |
```

Commit + push:
```bash
cd /Users/iorlas/Workspaces/agent-harness
git add docs/superpowers/plans/2026-04-14-agent-weiss-roadmap.md
git commit -m "roadmap: mark agent-weiss Plan 2 (Control Library Build-Out) complete"
git push
```

- [ ] **Step 2: Tag the milestone**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
git tag -a control-library -m "Plan 2 complete: 16 controls across universal + python + typescript profiles"
git push origin control-library
```

- [ ] **Step 3: Final sanity check**

Run from agent-weiss repo:
```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest -v
gh run list --repo yoselabs/agent-weiss --limit 1  # confirm latest CI green
```

Expected:
- All tests pass (~127)
- Latest CI run = `success`
- Tag `control-library` exists locally and on origin

---

## Plan-completion checklist

Before declaring Plan 2 done:
- [ ] All 20 tasks committed and pushed
- [ ] CI green on `main`
- [ ] `uv run pytest -v` passes locally with at least 127 tests
- [ ] All 16 controls have prescribed.yaml + check.sh + instruct.md + pass/fail fixtures (verified by `test_control_completeness.py`)
- [ ] All Rego policies have test siblings + pass `conftest verify` (verified by Task 19's `test_rego_unit_tests.py`)
- [ ] Roadmap updated in agent-harness repo: Plan 2 → Done
- [ ] Tag `control-library` pushed
- [ ] No TODO / TBD / "fix later" markers in new code
- [ ] Each Rego port preserves the source policy's deny rules verbatim (only package name changed)

## After Plan 2 completes

The natural next step is **Plan 3: Setup Workflow & Approval UX** — wires the verb-based approval interaction (`approve all`, `<numbers>`, etc.), backups, dry-run, and the per-anomaly reconciliation prompts. The control library Plan 2 ships becomes Plan 3's input: it knows what to propose, Plan 3 builds the apply/reject UX.

Plan 3 should also fold in Plan 1's review-flagged hardening items:
- `state.py:78` — use `copy.deepcopy(state._raw)` to prevent shallow-copy drift on multi-write runs
- `state.py` — store `schema_version` on `State`, validate on read
- `reconcile.py` — make orphan scan recursive (`rglob` instead of `iterdir`)
- `schemas.py` — add `id`-vs-path consistency check to `test_control_completeness.py`

These are small individual fixes but multiplied across Plan 3's writes-state-multiple-times-per-run flow they could mask bugs. Address them at Plan 3's task 1 (or as a tiny preflight plan).
