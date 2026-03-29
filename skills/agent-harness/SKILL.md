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
