# agent-weiss — Design Spec

**Date:** 2026-04-14
**Status:** Approved by Denis, ready for implementation planning
**Repo (target):** `yoselabs/agent-weiss` (to be created)
**Note:** Will live in a new repo. Currently drafted in `agent-harness/docs/superpowers/specs/` for convenience.

---

## 1. Product

A Claude Code skill (no CLI) that **sets up any codebase to be agent-ready and verifies that setup over time**.

Named after Grimoire Weiss from NieR — the white sentient grimoire that accompanies the protagonist. The skill is the codebase's grimoire: a knowledge companion that ensures the foundation is in place for AI agents to work effectively.

### What it does

1. Detects the project's stack (Python, TypeScript, Docker, etc.)
2. Matches applicable **profiles** (composable audit configurations)
3. Identifies what's missing or misconfigured for agent-readiness
4. Sets up missing pieces with per-change user approval (linters, hooks, policies, docs scaffolding)
5. Runs the configured checks once setup is verified
6. Produces two scores — **Setup** (must) and **Quality** (nice)
7. Maintains state in `.agent-weiss.yaml` so re-runs are idempotent and adaptive

### What it is NOT

- Not a runtime agent harness (Claude Code, Cursor, Codex are harnesses)
- Not LLM input/output guardrails (NeMo Guardrails, Bedrock Guardrails)
- Not a CLI tool (the skill IS the entry point)
- Not a one-shot setup wizard (it's a re-runnable audit + remediation loop)

---

## 2. Scope

### v1 ships

- **Profiles:** universal, python, typescript
- **Domains within those profiles:** docs, security, vcs, project-structure, quality, testing
- **~30–40 controls** total (~20–30 ported from agent-harness, ~10 new)
- **Setup workflow:** detect → propose → approve → write
- **Verify workflow:** run controls → score → report
- **State management:** `.agent-weiss.yaml` with overrides, custom-policy tracking, drift detection

### Target (deferred)

- **Profiles:** + docker, + node-cli, + python-cli, + python-web, + ts-web, + ts-library
- **Domains:** + agent-readiness-docs (CLAUDE.md/AGENTS.md/.cursorrules quality), + hooks (pre-commit/commit-msg patterns), + ci-cd (GitHub Actions templates), + mcp (.mcp.json setup)
- **Custom-policy review** (conflict detection, merge proposals, promotion suggestions)
- **Bundle update mechanism** (skill bundle versioning + drift refresh UX)

---

## 3. Architecture

### Hybrid execution model

Each control combines three artifacts:

| Artifact | Purpose | Required? |
|---|---|---|
| `prescribed.yaml` | Denis's recommended configuration for this control | Always |
| `check.sh` | Deterministic verification (runs tools, conftest, file tests) | Most controls |
| `policy.rego` (+ `policy_test.rego`) | Rego policy for structural config checks | When applicable |
| `instruct.md` | Agent-interpretable nuance (judgment calls, "why this matters") | Always |

**Dispatch in `check.sh`:**

| Check type | Mechanism | Example |
|---|---|---|
| Structural (config shape) | `conftest test -p policy.rego pyproject.toml` | "pyproject has `--strict-markers`" |
| Tool-wrapping | Run tool, parse output | `ruff check .` |
| Existence | `test -f` / `stat` | `test -f CLAUDE.md` |
| Judgment | Agent reads `instruct.md`, no script | "Does CLAUDE.md describe architecture well?" |

### Repository layout (skill bundle)

```
agent-weiss/
  skill.md                     # skill entry point
  profiles/
    universal/                 # always applies
      manifest.yaml            # profile-level metadata + domain references
      domains/
        docs/
          controls/
            agents-md-present/
              prescribed.yaml
              check.sh
              instruct.md
            readme-quality/
        security/
          controls/
            gitleaks-configured/
              prescribed.yaml
              check.sh
              policy.rego
              policy_test.rego
              instruct.md
            secrets-in-env/
        vcs/
          controls/
            gitignore-complete/
        project-structure/
    python/
      manifest.yaml
      domains/
        quality/
          controls/
            linter-configured/   # prescribes ruff
            formatter-configured/
            type-checker-configured/
        testing/
          controls/
            test-framework-present/
            coverage-threshold/
    typescript/
      manifest.yaml
      domains/
        quality/                 # prescribes biome
        testing/                 # prescribes vitest
    docker/                      # deferred to v2
```

### Profile composability

A project can match multiple profiles simultaneously. Example: a Python web service with a Dockerfile matches `universal + python + docker`. Each profile contributes its domains and controls. No ordering — all detected profiles apply.

Profile match is configurable. After detection, user confirms: "I detected python + docker. Sound right?" User can add/remove profiles in `.agent-weiss.yaml`.

---

## 4. State file: `.agent-weiss.yaml`

Lives at project root. Created on first run, updated on every subsequent run.

### Schema

```yaml
version: 1
generated_by: agent-weiss@<bundle_version>
profiles: [universal, python]    # confirmed by user

prescribed:
  python.quality.linter-configured:
    bundle_version: 1.2.3        # version of skill bundle when last synced
    last_synced: 2026-04-14
    overrides:
      tool: biome                # user chose non-prescribed tool
      reason: "team preference, established before adoption"

custom_policies:
  - path: .agent-weiss/policies/custom-no-print.rego
    notes: "team rule, added 2026-03-12"
    review_status: pending       # or: reviewed-no-conflict, reviewed-overlaps-prescribed, reviewed-promote-candidate

scores:
  setup:
    total: 92
    by_domain:
      docs: 100
      security: 100
      vcs: 90
      quality: 100
      testing: 85
  quality:
    total: 67
    by_check_kind:
      lint: 8                    # 8 issues found
      types: 0
      tests: 3                   # 3 failing
      security: 0

drift:
  - control: python.pyproject
    project_version: 1.2.0
    bundle_version: 1.2.3
    refresh_offered: true

last_scan: 2026-04-14T12:00:00+03:00
last_setup: 2026-04-14T11:55:00+03:00
```

### What gets written into the project

```
user-project/
  .agent-weiss.yaml                          # state file (above)
  .agent-weiss/
    policies/                                # copied from skill bundle
      python-pyproject.rego                  # has header: # Source: agent-weiss/python/quality/linter@v1.2.3
      python-pyproject_test.rego
      universal-gitignore.rego
      ...
    backups/<timestamp>/                     # files backed up before any overwrite
  .pre-commit-config.yaml                    # written/updated
  conftest.toml                              # written/updated
```

The `.agent-weiss/` directory is **owned by the skill** but transparent — engineers can inspect everything.

---

## 5. Bidirectional respect model

The defining behavior. Engineers retain full autonomy; the skill provides oversight without overwriting.

### Source classification

Every policy/config is one of:

| Source | Marker | Skill behavior |
|---|---|---|
| **Prescribed** (from skill bundle) | Header: `# Source: agent-weiss/python/quality/linter@v1.2.3` | Drift-checked. Version-managed. Refresh with diff preview when bundle updates. |
| **Custom** (engineer-added) | No skill header (or `# Source: custom`) | Respected as-is. Never overwritten. May be reviewed (opt-in). |
| **Override** (declared in `.agent-weiss.yaml`) | Override entry under `prescribed.<control>.overrides` | Skill applies override config. Reports as "deliberate divergence." |

### Custom-policy review (opt-in per scan)

When the engineer adds a custom policy, the skill can:

1. **Detect conflicts** — overlap or contradiction with a prescribed policy
2. **Propose merge/simplify** — "your `custom-no-print.rego` overlaps with prescribed `python-quality/no-debug-stmts` — consider replacing"
3. **Propose promotion** — "this looks broadly useful — want us to consider adding it to the bundle for everyone?"
4. **Propose removal** — "your `custom-import-order.rego` is now covered by prescribed — keep both, replace, or skip?"

All proposals require explicit approval. Skill never silently modifies custom files.

---

## 6. User loop (setup-first)

Single state-aware loop. Behavior varies based on `.agent-weiss.yaml` presence and content.

### Steps

1. **Detect** — read `.agent-weiss.yaml` if present; scan repo for stack signals (pyproject.toml, package.json, Dockerfile, lockfiles)
2. **Match profiles** — confirm with user: "I detected python + docker. Add or remove any?"
3. **Setup phase** — gap analysis + per-change approval:
   - For each control: what's missing? What's drifted from prescribed? What's custom-without-conflict?
   - Show plan: "We need to: install ruff, write `[tool.ruff]` section in pyproject.toml, write `.pre-commit-config.yaml`, copy 5 Rego policies into `.agent-weiss/policies/`, add `make check` target"
   - Per-change approval (with diff previews; default mode is review-each, not auto-apply)
   - Pre-write backup of any overwritten files to `.agent-weiss/backups/<timestamp>/`
   - Apply approved changes
4. **Verify phase** — smoke test:
   - Run all controls (`check.sh` for each — invokes ruff, conftest, gitleaks, etc.)
   - Anything failing here is a real problem, not a setup gap
5. **Score** — compute Setup score (config completeness) and Quality score (current code health)
6. **Report** — score breakdown by domain, list of findings, drift status, custom policies summary
7. **Update `.agent-weiss.yaml`** — overrides, custom-policy review status, last_synced versions, scores, drift records

### First run vs subsequent runs

| Phase | First run | Subsequent runs |
|---|---|---|
| Setup | Lots of changes proposed | Mostly drift detection (version bumps, new prescribed controls) |
| Verify | Usually all green (just set up) | Where real lint/test/security findings surface |
| Setup score | Establishes baseline | Tracks setup completeness over time |
| Quality score | Reflects post-setup state | Reflects current code health |

---

## 7. Two scores

| Score | Measures | Source |
|---|---|---|
| **Setup score** (must) | Is the project equipped for agent-friendly dev? | Configuration completeness — does each control have its prescribed setup in place (or a deliberate override)? |
| **Quality score** (nice) | Is the current code passing the configured checks? | Run-time results from `check.sh` invocations of linters/tests/scanners |

A project can have **Setup 100, Quality 60** (perfectly configured but accumulated issues) or **Setup 40, Quality 90** (barely configured, but clean code). Different concerns, different remediation paths.

### Reporting format

```
agent-weiss audit complete

SETUP SCORE: 92 / 100
  ✓ docs (universal)        100   CLAUDE.md, AGENTS.md, README all present
  ✓ security (universal)    100   gitleaks + osv-scanner configured
  ⚠ vcs (universal)          90   .gitignore complete, missing CODEOWNERS
  ✓ quality (python)        100   ruff + ty configured
  ⚠ testing (python)         85   pytest configured, coverage threshold missing

QUALITY SCORE: 67 / 100
  ⚠ lint:    8 ruff issues in src/handlers/
  ✓ types:   ty passing
  ✗ tests:   3 failing in tests/test_auth.py
  ✓ security: gitleaks clean, osv-scanner: 0 vulns

DRIFT: 1 prescribed policy updated since your last sync
CUSTOM: 2 custom policies present, no conflicts detected
```

---

## 8. Safety / trust mechanics (the vibe-coding dilemma)

The product's biggest risk: skill makes too many changes, user can't understand them, hits `git reset --hard`, never returns. Mitigations:

| Concern | Mitigation |
|---|---|
| Too many changes at once | Per-change approval. Default mode is review-each, not batch-apply. |
| "What did this even do?" | Each change shows WHY (from `instruct.md`) before approval. |
| "I want to undo" | Pre-write backups in `.agent-weiss/backups/<timestamp>/`. Restore command. |
| "I don't understand the change deeply" | Follow-up: "explain this control more deeply" — agent provides extended rationale. |
| "Don't ever touch X" | Override in `.agent-weiss.yaml` permanently silences a control or pins to a config. |
| "Sandbox first" | `--dry-run` mode shows plan without writing. |

---

## 9. Migration plan from agent-harness

agent-harness is **kept as-is, informally deprecated.** It continues to work for legacy users; no further development. Documentation will direct new users to agent-weiss.

| agent-harness asset | Migration to agent-weiss |
|---|---|
| Rego policies (`src/agent_harness/policies/<preset>/*.rego`) | Ported per-policy into `profiles/<lang>/domains/<domain>/controls/<control>/policy.rego` |
| Conftest runner pattern (`agent_harness.conftest.run_conftest()`) | `check.sh` invokes `conftest test` directly with the control's policy |
| Preset Python files (`presets/python/__init__.py`) | Become declarative `profiles/python/manifest.yaml` |
| Lint/fix CLI commands | Not migrated — skill IS the new entry point |
| Shared `conftest.py` | Re-bundled with skill if needed |
| Tests for policies (`*_test.rego`) | Migrated alongside their policy |
| WHAT/WHY/FIX docstring convention | Split: "what is required" → `prescribed.yaml`; "why it matters" → `instruct.md`; "how we check" → `policy.rego` or `check.sh` |

**Estimated mapping:** Each existing Rego policy → 1 control. ~20–30 controls in v1 from agent-harness migration alone, plus ~10 new controls (security, agent-readiness docs).

---

## 10. Out of scope (v1)

- Multi-language monorepos beyond simple stack composition (e.g., Python + TypeScript in same repo is supported via dual profiles, but advanced cross-stack rules are not)
- CI/CD template generation (deferred to target)
- Auto-installation of missing tools (skill recommends `uv add`/`pnpm add`, doesn't run installers)
- IDE integrations
- Hosted dashboard / cloud sync
- Team collaboration features (PR comments, GitHub Checks integration)
- Skill bundle version distribution mechanism (assume manual reinstall for v1)

---

## 11. Open questions for implementation planning

- Skill packaging: `.skill` directory? npm package? PyPI package? How does the user install agent-weiss?
- Bundle versioning: how does `.agent-weiss.yaml` tracking `bundle_version: 1.2.3` reconcile with the skill being installed locally? Embedded version manifest in the skill bundle?
- Tool installation: should skill `uv add`/`pnpm add` missing tools, or just instruct?
- Approval UX: per-change is the default, but what's the agent-conversation pattern? "I propose change 1 of 12, approve?" vs grouped batches?
- Score weighting: which controls weigh more? Equal weight per domain? Configurable?
- Custom-policy review trigger: opt-in per scan via flag, or always-on with ability to skip?

---

## 12. References

- **Caliber** (caliber-ai-org/ai-setup) — UX reference (scoring, refresh, diff preview, undo)
- **Factory.ai Agent Readiness** — competitor (commercial, 8 pillars, 5 maturity levels)
- **@kodus/agent-readiness** — competitor (OSS, framework-neutral, surface-level)
- **MegaLinter** — declarative `.mega-linter.yml` model (inspiration for `.agent-weiss.yaml`)
- **agent-harness** (yoselabs/agent-harness) — predecessor, source of Rego policies and conftest pattern
- **NieR: Replicant / NieR: Automata** — Grimoire Weiss is the namesake

---

## 13. Cross-references

- **P105 Yose Labs** (`~/Documents/Knowledge/Projects/105-yoselabs/`) — brand and product context
- **agent-harness CLAUDE.md** — Architecture conventions (preset/Rego pattern) inherited and adapted
