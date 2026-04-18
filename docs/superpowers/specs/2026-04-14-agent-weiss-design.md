# agent-weiss — Design Spec

**Date:** 2026-04-14
**Status:** Approved by Denis (post-review revision), ready for implementation planning
**Repo (target):** `yoselabs/agent-weiss` (to be created)
**Note:** Will live in a new repo. Currently drafted in `agent-harness/docs/superpowers/specs/` for convenience.
**Revision history:**
- 2026-04-14 v1 — initial design
- 2026-04-14 v2 — code-review revision: locked bundle versioning, replaced header-based source detection with state-file path+hash, added concrete score formulas, added Approval UX subsection, declared POSIX/WSL stance, added 4th source class (prescribed-locally-modified), added skill testing strategy.

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

### Platform support (v1)

- **macOS, Linux** — first-class
- **Windows via WSL** — supported same as Linux
- **Native Windows** — explicitly unsupported in v1; revisit on demand

This matches agent-harness's posture and aligns with how most Claude Code/Codex/Cursor workflows are run today.

---

## 2. Scope

### v1 ships

- **Profiles:** universal, python, typescript
- **Domains within those profiles:** docs, security, vcs, project-structure, quality, testing
- **~30–40 controls** total (~20–30 ported from agent-harness, ~10 new)
- **Setup workflow:** detect → propose → approve → write
- **Verify workflow:** run controls → score → report
- **State management:** `.agent-weiss.yaml` with overrides, custom-policy tracking, drift detection (path + content hash)

### Target (deferred)

- **Profiles:** + docker, + node-cli, + python-cli, + python-web, + ts-web, + ts-library
- **Domains:** + agent-readiness-docs (CLAUDE.md/AGENTS.md/.cursorrules quality), + hooks (pre-commit/commit-msg patterns), + ci-cd (GitHub Actions templates), + mcp (.mcp.json setup)
- **Custom-policy review** (conflict detection, merge proposals, promotion suggestions)
- **Bundle update mechanism** (skill bundle versioning + drift refresh against remote, not just bundled-on-install)
- **Native Windows support**

---

## 3. Architecture

### Hybrid execution model

Each control combines four artifacts:

| Artifact | Purpose | Required? |
|---|---|---|
| `prescribed.yaml` | Denis's recommended configuration for this control | Always |
| `check.sh` | Deterministic verification entry point (POSIX shell) | Most controls (omit for pure-judgment controls) |
| `policy.rego` (+ `policy_test.rego`) | Rego policy for structural config checks | When applicable |
| `instruct.md` | Agent-interpretable nuance (judgment calls, "why this matters") | Always |

`check.sh` is intentionally a thin POSIX shell entry point. Heavy logic stays in the tools it invokes (`conftest`, `ruff`, `gitleaks`, `osv-scanner`). This keeps the dispatch layer trivial and consistent across controls.

**Dispatch in `check.sh`:**

| Check type | Mechanism | Example |
|---|---|---|
| Structural (config shape) | `conftest test -p policy.rego pyproject.toml` | "pyproject has `--strict-markers`" |
| Tool-wrapping | Run tool, parse output | `ruff check .` |
| Existence | `test -f` / `stat` | `test -f CLAUDE.md` |
| Judgment | `check.sh` omitted; agent reads `instruct.md` and reports | "Does CLAUDE.md describe architecture well?" |

**Tool-missing behavior:** if `check.sh` requires a tool that isn't installed, it exits with a documented sentinel code (e.g., 127) and a one-line instruction (e.g., `install with: uv add ruff`). The skill treats this as **Setup-unmet** for that control (not Quality-failed). Auto-install is out of scope.

### Repository layout (skill bundle)

```
agent-weiss/
  skill.md                     # skill entry point
  bundle.yaml                  # version manifest (single source of truth for bundle version)
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
  fixtures/                     # used by skill self-tests
    profiles/<profile>/<domain>/<control>/
      pass/                     # fixture project where control should pass
      fail/                     # fixture project where control should fail
```

### Bundle versioning

**Single bundle version. All controls move together.** No per-control semver.

- `bundle.yaml` at the skill root is the only place a version lives.
- The state file (`.agent-weiss.yaml`) records which `bundle_version` was last synced for the project as a whole.
- Drift detection compares the version recorded in state vs the version in the currently-installed skill bundle.
- Controls that change content between bundles are detected via per-file content hashes in the bundle's manifest (see §4 and §5).

This drops the per-control `linter@v1.2.3` notation — controls don't have independent versions; the bundle does.

### Profile composability

A project can match multiple profiles simultaneously. Example: a Python web service with a Dockerfile matches `universal + python + docker`. Each profile contributes its domains and controls. **Profile order is not significant** — all detected profiles apply.

If two profiles define controls in the same domain (e.g., `universal/security/secrets-in-env` and `docker/security/secrets-in-env`), they coexist as separate controls under namespaced IDs (`universal.security.secrets-in-env`, `docker.security.secrets-in-env`). Profiles never override each other's controls; they accumulate.

Profile match is configurable. After detection, user confirms: "I detected python + docker. Sound right?" User can add/remove profiles in `.agent-weiss.yaml`.

---

## 4. State file: `.agent-weiss.yaml`

Lives at project root. Created on first run, updated on every subsequent run. **This file is the source of truth for which files in `.agent-weiss/policies/` came from the bundle vs. were added by the engineer.**

### Schema

```yaml
version: 1
generated_by: agent-weiss@1.2.3   # bundle version that wrote this state
bundle_version: 1.2.3              # bundle version last synced
profiles: [universal, python]      # confirmed by user

prescribed:
  python.quality.linter-configured:
    last_synced: 2026-04-14
    overrides:
      tool: biome                  # user chose non-prescribed tool
      reason: "team preference, established before adoption"

# Source map: which files in the project were copied from the bundle.
# Hash is content-addressed; mismatch = locally modified.
prescribed_files:
  .agent-weiss/policies/python-pyproject.rego:
    sha256: "abc123…"              # hash of the bundle copy at last sync
    bundle_path: profiles/python/domains/quality/controls/linter-configured/policy.rego
    last_synced: 2026-04-14
  .agent-weiss/policies/python-pyproject_test.rego:
    sha256: "def456…"
    bundle_path: profiles/python/domains/quality/controls/linter-configured/policy_test.rego
    last_synced: 2026-04-14
  .pre-commit-config.yaml:
    sha256: "789ghi…"
    bundle_path: profiles/universal/integration/pre-commit-config.yaml
    last_synced: 2026-04-14

custom_policies:
  - path: .agent-weiss/policies/custom-no-print.rego
    notes: "team rule, added 2026-03-12"
    review_status: pending

scores:
  setup:
    total: 88
    by_domain:
      docs: 100
      security: 100
      vcs: 75
      quality: 100
      testing: 50
  quality:
    total: 67
    by_check_kind:
      lint: 8
      types: 0
      tests: 3
      security: 0

drift:
  bundle:
    project_version: 1.2.0
    bundle_version: 1.2.3
    refresh_offered: true
  files:
    - path: .agent-weiss/policies/python-pyproject.rego
      status: locally_modified     # hash mismatch with last_synced
      action_offered: review

last_scan: 2026-04-14T12:00:00+03:00
last_setup: 2026-04-14T11:55:00+03:00
```

### What gets written into the project

```
user-project/
  .agent-weiss.yaml                          # state file (above)
  .agent-weiss/
    policies/                                # copied from skill bundle
      python-pyproject.rego                  # courtesy header: "# Managed by agent-weiss — see .agent-weiss.yaml"
      python-pyproject_test.rego
      universal-gitignore.rego
      ...
    backups/<timestamp>/                     # files backed up before any overwrite
  .pre-commit-config.yaml                    # written/updated; hooks include `conftest test -p .agent-weiss/policies/`
```

The header comment in copied files is **a courtesy, not load-bearing**. Source-of-truth is the `prescribed_files` map in `.agent-weiss.yaml`. If the header is removed or the file is renamed, the state file's path entry is what determines classification.

**`conftest.toml`** mentioned in v1 of this spec has been dropped — `conftest`'s policy directory is configured directly via `--policy` in the pre-commit hook command, no separate config file needed.

---

## 5. Bidirectional respect model (source classification)

The defining behavior. Engineers retain full autonomy; the skill provides oversight without overwriting.

### Source classification (4 classes)

For every file in `.agent-weiss/policies/` (and other tracked paths), the skill classifies based on `.agent-weiss.yaml`:

| Source | Detection | Skill behavior |
|---|---|---|
| **Prescribed (clean)** | Path is in `prescribed_files`; current content hash matches recorded `sha256` | Drift-checked against bundle. Refresh with diff preview when bundle updates. |
| **Prescribed (locally modified)** | Path is in `prescribed_files`; current content hash ≠ recorded `sha256` | Surface in drift report. Prompt: keep local mods (reclassify as custom), restore prescribed (overwrite local), or merge (interactive). |
| **Custom** (engineer-added) | Path is NOT in `prescribed_files`; file exists | Respected as-is. Never overwritten. May be reviewed (opt-in, deferred to v2). |
| **Override** (declared in `.agent-weiss.yaml`) | Entry under `prescribed.<control>.overrides` | Skill applies override config (skips writing prescribed, reports as "deliberate divergence"). |

**No file headers are load-bearing.** Headers in copied files are a human courtesy.

### What happens when the bundle updates a prescribed file

1. Skill reads `prescribed_files[path].sha256` (last synced) and `bundle.<bundle_path>.sha256` (current bundle).
2. If those don't match → bundle has updates for this file.
3. Skill also checks current project file's hash:
   - Matches `prescribed_files[path].sha256` → clean prescribed; offer simple refresh with diff preview.
   - Doesn't match → prescribed-locally-modified; offer 3-way: keep mods, restore, merge.
4. User approves. State file updates.

### Custom-policy review (deferred to v2)

When the engineer adds a custom policy, future versions can offer:
1. **Detect conflicts** — overlap or contradiction with a prescribed policy
2. **Propose merge/simplify** — "your custom-no-print.rego overlaps with prescribed python-quality/no-debug-stmts"
3. **Propose promotion** — "this looks broadly useful — open an issue at github.com/yoselabs/agent-weiss/issues/new?template=promote-policy with this policy"
4. **Propose removal** — "your custom-import-order.rego is now covered by prescribed — keep both, replace, or skip?"

In v1, promotion is a manual GitHub issue link with a template. Automation deferred. All proposals require explicit user approval; skill never silently modifies custom files.

---

## 6. User loop (setup-first)

Single state-aware loop. Behavior varies based on `.agent-weiss.yaml` presence and content.

### Steps

1. **Detect** — read `.agent-weiss.yaml` if present; scan repo for stack signals (pyproject.toml, package.json, Dockerfile, lockfiles)
2. **Match profiles** — confirm with user: "I detected python + docker. Add or remove any?"
3. **Setup phase** — gap analysis + per-change approval (see Approval UX below)
4. **Verify phase** — smoke test:
   - Run all controls' `check.sh` (where defined)
   - Tool-missing exits → control is Setup-unmet, prompt user with install command
   - Real failures (lint issues, test failures, security findings) → Quality-failed
5. **Score** — compute Setup score and Quality score per formulas (see §7)
6. **Report** — score breakdown by domain, list of findings, drift status, custom policies summary
7. **Update `.agent-weiss.yaml`** — overrides, custom-policy review status, prescribed_files map updates, scores, drift records

### Approval UX (the conversation pattern)

Default mode is **per-change review**, batched by domain for context. The agent-led conversation looks like:

```
> Setup phase plan: 12 changes across 4 domains.

  docs (universal) — 2 changes
    1. Create AGENTS.md (template attached)
    2. Update CLAUDE.md to reference AGENTS.md

  security (universal) — 5 changes
    3. Install gitleaks (run: brew install gitleaks)
    4. Add .pre-commit-config.yaml hook for gitleaks
    5. Copy policy: universal-secrets-in-env.rego
    ...

  Reply with: 'approve all', 'approve docs', '1,3,5', 'skip 2', 'explain 4', 'dry-run', or 'cancel'
```

**Interaction rules:**

- User can approve all, approve a whole domain, approve specific numbers, skip specific numbers, or ask for an explanation on any change.
- Declining a change does not auto-decline dependent changes. The agent re-evaluates dependencies after each batch and may prompt: "you skipped #4 (gitleaks pre-commit hook). Should #5 (gitleaks Rego policy) still be copied? It will be unused without #4."
- "explain N" reads `instruct.md` for that control and surfaces an extended rationale.
- "dry-run" mode applies nothing, writes a report to `.agent-weiss/dry-run-<timestamp>.md`, and exits.

Subsequent runs typically have far fewer changes (mostly drift refreshes), so the same pattern works gracefully when there are 1–3 items.

### First run vs subsequent runs

| Phase | First run | Subsequent runs |
|---|---|---|
| Setup | Lots of changes proposed | Mostly drift detection (bundle version bumps, new prescribed controls) |
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

### Setup score formula

For each control:
- **100** — control is satisfied (prescribed config in place, files present, override deliberately declared with reason)
- **0** — control is unmet (missing files, missing config, tool not installed, or `check.sh` exited with Setup-unmet sentinel)

Per-domain Setup score = average of its controls' scores.
Total Setup score = average of per-domain scores. (All domains weighted equally in v1; configurable weighting deferred.)

**Override = pass.** A user who deliberately declares an override (with `reason` field) is making a conscious choice. Setup score should reward "you've thought about this" equally with "you accepted the prescribed default." Both are explicit decisions.

### Quality score formula

For each control with a `check.sh`:
- **100** — `check.sh` exited 0 (passing)
- **0** — `check.sh` exited non-zero with a real failure (not the Setup-unmet sentinel)
- **excluded from denominator** — control is Setup-unmet (we can't measure quality of an absent linter)

Per-domain Quality score = average of its controls' Quality scores (excluding Setup-unmet controls).
Total Quality score = average of per-domain Quality scores.

If all controls in a domain are Setup-unmet, that domain reports `n/a` for Quality and is excluded from the total.

### Reporting format

```
agent-weiss audit complete

SETUP SCORE: 88 / 100
  ✓ docs (universal)        100   CLAUDE.md, AGENTS.md, README all present
  ✓ security (universal)    100   gitleaks + osv-scanner configured
  ⚠ vcs (universal)          75   3/4 controls met, missing CODEOWNERS
  ✓ quality (python)        100   ruff + ty + formatter all configured
  ⚠ testing (python)         50   1/2 controls met, coverage threshold missing

QUALITY SCORE: 67 / 100
  ⚠ lint:    8 ruff issues in src/handlers/
  ✓ types:   ty passing
  ✗ tests:   3 failing in tests/test_auth.py
  ✓ security: gitleaks clean, osv-scanner: 0 vulns

DRIFT: bundle 1.2.3 has updates for 1 prescribed file you've kept clean
        and 1 file you've locally modified (review needed)
CUSTOM: 2 custom policies present
```

---

## 8. Safety / trust mechanics (the vibe-coding dilemma)

The product's biggest risk: skill makes too many changes, user can't understand them, hits `git reset --hard`, never returns. Mitigations:

| Concern | Mitigation |
|---|---|
| Too many changes at once | Per-change approval. Default mode is review-each (batched by domain), not batch-apply. |
| "What did this even do?" | Each change shows WHY (from `instruct.md`) before approval. |
| "I want to undo" | Pre-write backups in `.agent-weiss/backups/<timestamp>/`. Restore command. |
| "I don't understand the change deeply" | "explain N" command reads `instruct.md` for extended rationale. |
| "Don't ever touch X" | Override in `.agent-weiss.yaml` permanently silences a control or pins to a config. |
| "Sandbox first" | `dry-run` mode shows plan without writing; exports report to `.agent-weiss/dry-run-<timestamp>.md`. |
| "Tool not installed and I don't want to install it" | Tool-missing → Setup-unmet. User can decline to install; control stays unmet but doesn't block other progress. |
| "I locally modified a prescribed file and the bundle updated it" | Prescribed-locally-modified detection. 3-way prompt: keep mods (reclassify as custom), restore, or merge interactively. |

---

## 9. Migration plan from agent-harness

agent-harness is **kept as-is, informally deprecated.** It continues to work for legacy users; no further development. Documentation will direct new users to agent-weiss.

### Asset migration

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

### Skill testing strategy

Each control ships with **fixture projects** under `agent-weiss/fixtures/profiles/<profile>/<domain>/<control>/`:

- `pass/` — minimal project where the control should report as satisfied
- `fail/` — minimal project where the control should report as unmet/failed

A test runner walks every fixture and asserts the expected outcome:

```
pytest tests/skill/test_controls.py
  for each control:
    run check.sh against pass/  → expect exit 0
    run check.sh against fail/  → expect exit non-zero
    run policy_test.rego        → expect all assertions pass (existing pattern from agent-harness)
```

This gives us a single command to verify every control end-to-end, mirroring `make test` in agent-harness.

---

## 10. Out of scope (v1)

- Multi-language monorepos beyond simple stack composition (Python + TypeScript via dual profiles is supported; advanced cross-stack rules are not)
- CI/CD template generation (deferred to target)
- Auto-installation of missing tools (skill instructs but never runs `uv add`/`pnpm add`/`brew install`)
- IDE integrations
- Hosted dashboard / cloud sync
- Team collaboration features (PR comments, GitHub Checks integration)
- Skill bundle update against a remote (v1 assumes reinstall-to-update — pin one version at install time, drift detection is local)
- Native Windows support (POSIX/WSL only in v1)
- Custom-policy automated review (conflict/merge/promotion) — deferred to v2
- Score weighting configuration (equal weighting in v1)

---

## 11. Open questions for implementation planning

These remain open and should be resolved during plan-writing or early implementation:

- **Skill packaging:** `.skill` directory, npm package, PyPI package, or installer script? How does a user install agent-weiss? (Affects how `bundle.yaml` ships.)
- **Tool-installation prompt format:** which exact command per OS? (e.g., `brew install gitleaks` vs `apt install gitleaks` vs `nix-shell -p gitleaks`.) Probably a `prescribed.yaml` field.
- **`bundle.yaml` schema:** what exactly does the bundle manifest contain? Per-file SHA index? Profile metadata? Versions of bundled tool configs? Settle in plan-writing.
- **Custom-policy review trigger (when v2 lands):** opt-in per scan via flag, or always-on with skip option? Defer until v2 design.

---

## 12. References

- **Caliber** (caliber-ai-org/ai-setup) — UX reference. Adopted: scoring, refresh pattern, diff preview, undo, natural-language refinement. Rejected: agent-config-only scope (Caliber generates CLAUDE.md/cursorrules; we go deeper into deterministic gates).
- **Factory.ai Agent Readiness** — competitor (commercial, 8 pillars, 5 maturity levels). Closed-source.
- **@kodus/agent-readiness** — competitor (OSS, framework-neutral, surface-level — mostly file-existence checks).
- **MegaLinter** — declarative `.mega-linter.yml` model (inspiration for `.agent-weiss.yaml` override layer).
- **agent-harness** (yoselabs/agent-harness) — predecessor, source of Rego policies and conftest pattern.
- **NieR: Replicant / NieR: Automata** — Grimoire Weiss is the namesake. Pronounced "vice" (German), per the game.

---

## 13. Cross-references

- **P105 Yose Labs** (`~/Documents/Knowledge/Projects/105-yoselabs/`) — brand and product context
- **agent-harness CLAUDE.md** — Architecture conventions (preset/Rego pattern) inherited and adapted
