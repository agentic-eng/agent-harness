# Skill Product Experience + Docs Update

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign SKILL.md as a guided product experience (scan → plan → approve → execute → report), update CONTRIBUTING.md to use agent-harness for development, and update README.md to reflect current state.

**Architecture:** SKILL.md is rewritten from scratch with a clear 3-phase flow: Discovery (scan everything, present findings), Planning (present A→B diff, challenge issues, get approval), Execution (apply, verify, report). CONTRIBUTING.md and README.md are updated to reflect current codebase.

**Tech Stack:** Markdown (no code changes)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `skills/agent-harness/SKILL.md` | The product experience — guided setup workflow for AI agents |
| `CONTRIBUTING.md` | Developer guide for contributing to agent-harness (uses agent-harness itself) |
| `README.md` | Public-facing project overview with current stats |

---

### Task 1: Rewrite SKILL.md as product experience

**Files:**
- Modify: `skills/agent-harness/SKILL.md`

The new SKILL.md has three phases, not numbered steps. Nothing is silently skipped. Every evaluation is visible.

- [ ] **Step 1: Read the current SKILL.md**

Read `skills/agent-harness/SKILL.md` to understand its full current content.

- [ ] **Step 2: Write the new SKILL.md**

Replace the entire file with the content below. Keep the frontmatter unchanged.

```markdown
---
name: agent-harness
description: "Deterministic quality gates for AI agents. Use when setting up a project, when lint fails, or when agent output is noisy. Triggers: 'set up harness', 'check harness', new project, first commit."
---

# Agent Harness

Deterministic controls (linters, type checkers, formatters, coverage gates) that constrain AI agent behavior automatically.

## The Experience

Agent Harness setup is a guided process. You scan, plan, and execute — nothing is silently skipped, nothing is assumed OK. The user sees every decision.

**Three phases:**

```
Phase 1: DISCOVER     →  Phase 2: PLAN        →  Phase 3: EXECUTE
Scan everything.         Present A→B diff.        Apply approved changes.
Challenge what's odd.    Get approval.             Verify. Report.
```

---

## Phase 1: Discover

Scan the full project state. Present every finding — even "looks good" gets a line.

### 1.1 Detect stacks and subprojects

```bash
agent-harness detect
```

Report what was detected and what was NOT detected. If a stack seems missing (e.g., Dockerfile exists but Docker not detected), say so.

### 1.2 Run diagnostics

```bash
agent-harness init            # report mode — no changes
```

Capture the output. This is the baseline.

### 1.3 Audit Makefiles

Read every Makefile in the project (root + all subprojects). Skip `node_modules`, `.venv`, `vendor`, `dist`. Also read `.pre-commit-config.yaml` if it exists.

**Check each of these — report findings for ALL, not just failures:**

| Check | What to look for |
|-------|-----------------|
| Duplicated work | Makefile runs tools agent-harness already runs (`ruff`, `ty`, `biome`, `hadolint`) |
| Bypassed tools | Makefile runs `ruff` but not `ty` (or vice versa) — skipping a gate |
| Conflicting fix targets | Multiple `make fix` targets running same formatter with different configs |
| Missing delegation | Root Makefile should call `agent-harness lint`, not individual tools |
| Pre-commit misalignment | Hook runs `make lint` but Makefile doesn't include agent-harness |
| Missing fix-before-lint | Pre-commit should run fix BEFORE lint |
| Stale targets | Bootstrap targets for tools agent-harness manages |
| Redundant security tooling | `pip-audit`, `npm audit`, or `gitleaks` targets — replace with `agent-harness security-audit` |

### 1.4 Audit CLAUDE.md

Read `CLAUDE.md` (if it exists). Check for these instructions:

**All projects must mention:**
- `make check` (or full quality gate command)
- `make lint` or `agent-harness lint`
- `make fix` or `agent-harness fix`
- Pre-commit hooks run automatically
- Never truncate lint/test output

**Python projects must also mention:**
- `make test` (with coverage)
- `make coverage-diff` (diff-cover)

**JavaScript projects must also mention:**
- `make test`
- Biome for formatting/linting

Report: "CLAUDE.md covers X, Y, Z. Missing: A, B."

### 1.5 Audit .gitignore

Check completeness against stack templates. Report:
- How many patterns exist vs expected
- Any stale patterns for stacks no longer in the project
- Any duplicates or near-duplicates

### 1.6 Check security tooling

```bash
agent-harness security-audit
```

Report dependency vulnerabilities and any detected secrets.

### 1.7 Check pre-commit hooks

Report whether hooks are installed, what they run, and whether they align with agent-harness.

---

### Discovery Report

After all checks, present a structured report:

```
## Discovery Report

### Stacks: Python, Docker (2 subprojects detected)

### Findings

✅ .agent-harness.yml — exists, stacks correct
⚠️  Makefile — runs `ruff` directly instead of `agent-harness lint`
⚠️  Makefile — has `pip-audit` target, redundant with `agent-harness security-audit`
✅ .pre-commit-config.yaml — fix-before-lint, correct hooks
⚠️  CLAUDE.md — mentions lint but not `make check`
✅ .gitignore — 142 patterns, complete for Python + macOS
⚠️  .gitignore — 12 Dagster patterns from removed stack
✅ Security audit — no vulnerabilities, no secrets
❌ Pre-commit hooks — not installed

### Summary: 4 findings to address, 4 checks passed
```

Every check produces a line. ✅ for pass, ⚠️ for fixable, ❌ for blocking.

---

## Phase 2: Plan

Present the changes needed to go from current state (A) to target state (B). Group by file.

### 2.1 Present the plan

```
## Setup Plan

### Makefile (rewrite lint/fix/check targets)

Current:
  lint: @uv run ruff format --check && @uv run ruff check
  fix: uv run ruff check --fix && uv run ruff format

Proposed:
  lint: @agent-harness lint
  fix: @agent-harness fix
  check: @agent-harness lint && uv run pytest tests/ -v && agent-harness security-audit

Reason: Makefile runs ruff directly, bypassing ty and conftest.
Agent-harness runs all three. Consolidate.

### Makefile (remove pip-audit target)

Current: audit: @uvx pip-audit
Proposed: (remove — agent-harness security-audit covers this)

### CLAUDE.md (add make check reference)

Add: "Full quality gate: `make check` — runs lint, test, security-audit."

### .gitignore (remove 12 stale Dagster patterns)

Remove lines 45-56 (Dagster patterns — stack removed from project).

### Pre-commit hooks (install)

Run: prek install

### agent-harness init --apply

Creates/updates: .agent-harness.yml, .yamllint.yml
```

### 2.2 Challenge questionable setups

If anything looks intentional but wrong, ask about it:

> "Your Makefile has a `deploy` target that runs `docker compose up -d` without checking lint first. Is this intentional, or should deploy depend on `make check`?"

Challenge by reasoning first (internally), then presenting the question. Don't challenge obvious things — only things where the user's intent is ambiguous.

### 2.3 Get approval

> "This is the full plan — N changes across M files. Approve to proceed, or tell me what to adjust."

Wait for explicit approval before making any changes.

---

## Phase 3: Execute

Apply all approved changes, verify, report.

### 3.1 Apply init fixes

```bash
agent-harness init --apply
```

### 3.2 Apply Makefile and config changes

Execute each change from the approved plan. For judgment calls (CLAUDE.md edits, .gitignore cleanup), integrate naturally — don't dump template blocks.

### 3.3 Install pre-commit hooks

```bash
prek install                  # or: pre-commit install
```

If prek fails with "core.hooksPath set":
```bash
git config --unset-all --local core.hooksPath
prek install
```

### 3.4 Deep security scan (first time only)

```bash
agent-harness security-audit-history
```

If secrets are found, they must be rotated. Add fingerprints to `.gitleaksignore` only for confirmed false positives.

### 3.5 Verify

```bash
make check                    # must pass — full quality gate
```

If it fails, fix issues and re-run until green.

### 3.6 Commit

Commit all generated/modified config files.

### 3.7 Report

Present the final report:

```
## Setup Complete

### Changes made
- Makefile: consolidated lint/fix/check targets to agent-harness
- Makefile: removed redundant pip-audit target
- CLAUDE.md: added make check reference
- .gitignore: removed 12 stale Dagster patterns
- .pre-commit-config.yaml: created (fix + lint hooks)
- .agent-harness.yml: created (stacks: python, docker)
- .yamllint.yml: created
- Pre-commit hooks: installed

### Verification
- make check: ✅ PASSED (10 lint checks, 45 tests, security audit clean)

### Skipped (with reason)
- .gitignore append: no missing patterns (already complete)
- Biome config: not a JavaScript project

### Manual attention needed
- None
```

Every action taken gets a line. Every check skipped gets a line with a reason. Nothing is invisible.

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `agent-harness detect` | Show detected stacks and subprojects |
| `agent-harness init` | Diagnose setup (report mode) |
| `agent-harness init --apply` | Apply auto-fixes and create missing config files |
| `agent-harness lint` | Run all checks — fast, pass/fail, blocks commits |
| `agent-harness fix` | Auto-fix (ruff, biome), then lint |
| `agent-harness security-audit` | Scan working dir for vulnerable deps + leaked secrets |
| `agent-harness security-audit-history` | Deep scan full git history for leaked secrets (slow, run once) |

## When to Use

- **Setting up a project** — run the full 3-phase experience above
- **Lint failures** — `agent-harness lint`, read errors, fix
- **After changing configs** — `agent-harness init` to re-diagnose
- **Monorepo** — all commands auto-discover subprojects

## When NOT to Use

- Business logic, architecture, domain modeling
- Deployment operations (use deployment-platform skill)
- Fixing one specific tool (help directly, don't run full setup)

## How It Works

Agent-harness auto-detects project stacks (Python, JavaScript, Docker, Dokploy) and runs the right checks. Every error message is actionable.

### Three layers

| Layer | What | When |
|-------|------|------|
| **lint** | "Is this gate broken?" Ruff, ty, conftest, yamllint, file length, gitignore, pre-commit | Every commit |
| **init** | "Is this gate configured well?" Config quality, completeness, missing tools | On-demand |
| **skill** | "Is this setup optimal?" Judgment calls — CLAUDE.md audit, .gitignore cleanup, Makefile consolidation | During setup |

When a user challenges a lint rule, read the WHY block from the check file or Rego policy. When a user challenges an init recommendation, check `presets/*/setup.py`.

## Conftest Exceptions

Individual conftest policies can be skipped per file via `conftest_skip` in `.agent-harness.yml`:

```yaml
docker:
  conftest_skip:
    scripts/autonomy/Dockerfile:
      - dockerfile.user
      - dockerfile.healthcheck
```

**Valid exception IDs:**

| ID | What it skips |
|----|---------------|
| `dockerfile.user` | USER instruction requirement |
| `dockerfile.healthcheck` | HEALTHCHECK instruction requirement |
| `dockerfile.cache` | `--mount=type=cache` on dep install |
| `dockerfile.secrets` | Secret detection in ENV/ARG |
| `dockerfile.layers` | Layer ordering (deps before source) |
| `dockerfile.base_image` | Alpine + musl-sensitive stack warning |
| `compose.services_healthcheck` | Service healthcheck requirement |
| `compose.services_restart` | Restart policy requirement |
| `compose.services_ports` | 0.0.0.0 port binding warning |
| `compose.images_build` | No build directive |
| `compose.images_mutable_tag` | Mutable tag + pull_policy |
| `compose.images_implicit_latest` | No-tag implicit :latest |
| `compose.images_pin_own` | Own image pinning |
| `compose.escaping` | Bare $ in environment values |
| `compose.hostname` | Hostname on dokploy-network |
| `compose.volumes` | Bind mount detection |
| `compose.configs` | Inline config content |
| `dokploy.traefik_enable` | traefik.enable=true requirement |
| `dokploy.traefik_network` | dokploy-network requirement |

## Monorepo Support

- `agent-harness lint` auto-discovers subprojects via git-aware file discovery
- Git root is resolved automatically — gitignore and pre-commit checks use the repo root
- Each subproject can have its own `.agent-harness.yml` for stack overrides
- Docker preset discovers all Dockerfiles in the tree (not just root)

## Guidance

Read these files when writing new Docker or Python code:

- **`docker-guidance.md`** — healthcheck recipes, dependency chains, migration patterns, config file strategy, base image selection
- **`python-guidance.md`** — why each pyproject.toml knob matters
- **`monorepo-guidance.md`** — subproject pre-commit traps, redundant configs
```

- [ ] **Step 3: Verify the file is well-formed**

Read the file back and check for any formatting issues.

- [ ] **Step 4: Commit**

```bash
git add skills/agent-harness/SKILL.md
git commit -m "feat: redesign SKILL.md as guided product experience (discover → plan → execute)"
```

---

### Task 2: Update CONTRIBUTING.md

**Files:**
- Modify: `CONTRIBUTING.md`

- [ ] **Step 1: Read the current CONTRIBUTING.md**

Read `CONTRIBUTING.md` to understand its current content.

- [ ] **Step 2: Write the updated CONTRIBUTING.md**

Replace the entire file. Key changes:
- Add "We use agent-harness to develop agent-harness" section
- Update dev setup to use `make check`
- Reference current architecture (git-aware discovery, conftest exceptions)
- Update test counts and tool references
- Fix stale reference to `src/agent_harness/stacks/` (now `presets/`)

```markdown
# Contributing to Agent Harness

Agent Harness enforces its own rules. We use agent-harness to develop agent-harness.

## Development setup

```bash
git clone https://github.com/yoselabs/agent-harness
cd agent-harness
uv sync                          # install dev deps
uv tool install -e .             # install CLI globally from source
agent-harness lint               # verify everything passes
```

## Quality gate

Before every commit (enforced by pre-commit hooks):

```bash
make check                       # lint + test + security-audit
```

This runs:
- `agent-harness lint` — 10 checks (ruff, ty, conftest, yamllint, etc.)
- `uv run pytest tests/ -v` — 201 Python tests
- `conftest verify` — 109 Rego policy tests
- `agent-harness security-audit` — dependency + secret scanning

## Adding a new Rego policy

One file per concern, one concern per file.

### 1. Decide: is it deterministic?

The harness only contains deterministic controls — tools that produce a pass/fail verdict without human judgment. If a rule requires interpretation, it's guidance (document it in the skill), not a policy.

### 2. Choose the right directory

- `src/agent_harness/policies/dockerfile/` — Dockerfile rules
- `src/agent_harness/policies/compose/` — Docker Compose rules
- `src/agent_harness/policies/dokploy/` — Dokploy/Traefik rules
- `src/agent_harness/policies/python/` — pyproject.toml / Python config rules
- `src/agent_harness/policies/gitignore/` — .gitignore rules

### 3. Write the .rego file

```rego
package dockerfile.my_concern

# One-line description.
# Why this matters for AI agents.
#
# Input: <describe the parsed data structure>

import rego.v1

default _exceptions := []

_exceptions := data.exceptions if {
    data.exceptions
}

deny contains msg if {
    not "dockerfile.my_concern" in _exceptions
    # your logic here
    msg := "Actionable error message — what's wrong and how to fix it"
}
```

**Conventions:**
- One file per concern (e.g., `layers.rego`, `cache.rego`)
- Package name matches directory + filename: `policies/dockerfile/layers.rego` → `package dockerfile.layers`
- Only `deny` rules. No `warn`.
- Error messages must be actionable — tell the agent what to do
- WHAT/WHY/WITHOUT IT/FIX comment block at top
- Always include `_exceptions` guard so policies can be skipped via `conftest_skip`

### 4. Write the test file

Every policy needs a `_test.rego` sibling with at least:

```rego
package dockerfile.my_concern_test

import rego.v1
import data.dockerfile.my_concern

test_bad_input_fires if {
    my_concern.deny with input as [...]
}

test_good_input_passes if {
    count(my_concern.deny) == 0 with input as [...]
}

test_exception_skips if {
    count(my_concern.deny) == 0 with input as [...]
        with data.exceptions as ["dockerfile.my_concern"]
}
```

### 5. Write fixture files

Place in `tests/fixtures/<directory>/`:
- `bad_*.Dockerfile` — triggers the deny
- `good_*.Dockerfile` — passes clean

Bad fixtures should ONLY fail on the rule being tested. Include USER, HEALTHCHECK, cache mount, etc. so they don't trigger unrelated rules.

### 6. Verify

```bash
# Rego unit tests
conftest verify --policy src/agent_harness/policies/dockerfile/

# Fixture tests
conftest test tests/fixtures/dockerfile/*.Dockerfile \
  --parser dockerfile \
  -p src/agent_harness/policies/dockerfile/ \
  --all-namespaces

# Full quality gate
make check
```

### 7. Update exception ID table

Add the new exception ID to `skills/agent-harness/SKILL.md` in the Conftest Exceptions table.

## Adding a new preset

1. Create `presets/<name>/` with `__init__.py` implementing `Preset`
2. Add individual check files (one per tool, with WHAT/WHY/WITHOUT IT/FIX docstring)
3. Add `<Name>Preset()` to `registry.py`
4. Add Rego policies to `policies/<name>/` if needed
5. Run `make check`

## Adding a new check module

Create a new file in `src/agent_harness/presets/<stack>/`. Follow the existing pattern:

- Function takes `project_dir: Path` and returns `CheckResult` (or `list[CheckResult]`)
- Use `run_check()` from `agent_harness.runner` for subprocess execution
- Wire the call into the preset's `run_checks()` method

## Evaluating community rules

Before writing a custom Rego rule, check if an existing tool covers it:

1. **Does hadolint cover it?** (Dockerfile shell practices) → Don't duplicate
2. **Does ruff cover it?** (Python code patterns) → Don't duplicate
3. **Does yamllint cover it?** (YAML syntax) → Don't duplicate
4. **Does a conftest community policy exist?** → Evaluate for adoption
5. **Does Trivy's built-in check cover it?** → Note the DS-* ID, write our own (Trivy is too slow)

If an existing tool covers it, don't duplicate in Rego.

### When NOT to write a rule

- **It requires file existence checks** — conftest parses content, not filesystem
- **It requires cross-file analysis** — conftest checks one file at a time
- **It's a judgment call** — document as guidance in the skill, not as a Rego policy
- **An existing tool does it better** — hadolint, ruff, yamllint have years of battle-tested rules

## Tool stack

| Tool | Purpose | Why this one |
|------|---------|-------------|
| conftest | Rego policies for any config file | Only tool that parses TOML + Dockerfile + YAML + JSON + .gitignore |
| hadolint | Dockerfile shell best practices | 12K stars, maintained, comprehensive |
| yamllint | YAML syntax + duplicate key detection | Catches duplicate keys conftest's parser silently merges |
| ruff | Python lint + format | 46K stars, fastest Python linter |
| ty | Python type checking | Astral's type checker, fast |

## Code style

```bash
make fix                         # auto-format + lint
```

Follow existing patterns. Ruff handles formatting automatically.
```

- [ ] **Step 3: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: update CONTRIBUTING.md — use agent-harness for development, current architecture"
```

---

### Task 3: Update README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read the current README.md**

Read `README.md` to understand its current content.

- [ ] **Step 2: Update stats and outdated sections**

Make these specific changes:

**Line 7** — Update rule count and stats:
```
Old: 36 rules &middot; 5 stacks &middot; <500ms &middot; Zero config
New: 44 rules &middot; 5 stacks &middot; <500ms &middot; Zero config
```

**Line 103** — Update Docker conftest description to mention multi-Dockerfile discovery:
```
Old: | **conftest** | Layer ordering, cache mounts, USER directive, HEALTHCHECK, secrets in ENV/ARG, base image pinning |
New: | **conftest** | Layer ordering, cache mounts, USER directive, HEALTHCHECK, secrets in ENV/ARG, base image pinning (discovers all Dockerfiles in tree) |
```

**Configuration section (after line 148)** — Add conftest_skip example:

After the existing YAML block, add:

```markdown

### Conftest Exceptions

Skip individual policies per file when legitimate:

```yaml
docker:
  conftest_skip:
    scripts/autonomy/Dockerfile:
      - dockerfile.user        # runs as root intentionally
      - dockerfile.healthcheck # not a service
```

See [SKILL.md](skills/agent-harness/SKILL.md#conftest-exceptions) for the full list of exception IDs.
```

**Commands table (line 152-157)** — Add security commands:

```markdown
| Command | Description |
|---------|-------------|
| `agent-harness detect` | Show detected stacks and subprojects |
| `agent-harness init` | Scaffold configs, Makefile, show tool availability |
| `agent-harness init --apply` | Apply auto-fixes and create missing config files |
| `agent-harness lint` | Run all checks — exits non-zero on failure |
| `agent-harness fix` | Auto-fix (ruff, biome), then lint |
| `agent-harness security-audit` | Scan working dir for vulnerable deps + leaked secrets |
| `agent-harness security-audit-history` | Deep scan full git history for leaked secrets |
```

**Status section (line 244-246)** — Update counts:
```
Old: **Current:** 36 Rego policies, 5 stacks (Python, JavaScript, Docker, Dokploy, Universal), 69 Python tests, 87 Rego tests.
New: **Current:** 44 Rego deny rules, 5 stacks (Python, JavaScript, Docker, Dokploy, Universal), 201 Python tests, 109 Rego tests.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update README.md — current stats, conftest exceptions, security commands"
```

---

### Task 4: Run full quality gate

- [ ] **Step 1: Run make check**

```bash
make check
```

Expected: All pass.

- [ ] **Step 2: Fix any issues**

If any check fails, fix and re-run.

- [ ] **Step 3: Final commit if needed**

Only if fixes were required in step 2.
