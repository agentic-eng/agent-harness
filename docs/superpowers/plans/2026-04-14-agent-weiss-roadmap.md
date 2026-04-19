# agent-weiss Roadmap

**Date:** 2026-04-14
**Source spec:** `docs/superpowers/specs/2026-04-14-agent-weiss-design.md` (4 review rounds, approved)
**Project:** P105 Yose Labs / agent-weiss
**Status:** Active

This roadmap is the program-level coordination document for agent-weiss. It enumerates all sub-plans, captures cross-cutting decisions, defines dependencies, and serves as the persistence layer for design decisions that span multiple plans.

**Update this file** whenever a plan completes, scope changes, or a new cross-cutting decision lands.

---

## Cross-cutting decisions (locked)

All plans MUST honor these. They came out of the brainstorm + 4 spec review rounds and are not up for renegotiation without a spec revision.

### Identity & branding

| Decision | Value |
|---|---|
| Product name | `agent-weiss` (Grimoire Weiss from NieR; pronounced "vice") |
| Org | `yoselabs` (寄せ = Go endgame precision) |
| Target repo | `yoselabs/agent-weiss` (to be created) |
| State file | `.agent-weiss.yaml` at project root |
| Bundle root env var | `AGENT_WEISS_BUNDLE` |
| Predecessor (deprecated) | `yoselabs/agent-harness` (kept as-is, no further development) |

### Platform & distribution

| Decision | Value |
|---|---|
| Platforms | macOS, Linux, Windows-via-WSL only. Native Windows unsupported in v1. |
| Distribution channels (v1) | **3 mirrors of one bundle:** Claude Code marketplace (primary) + PyPI + npm |
| Bundle install paths | Claude: `~/.claude/plugins/yoselabs/agent-weiss/`. PyPI: `<env>/share/agent-weiss/`. npm: `<prefix>/share/agent-weiss/`. |
| Bundle resolution order | `AGENT_WEISS_BUNDLE` env var first, then probe (Claude → PyPI → npm) |
| Updates | Re-run install command. No remote-fetch in v1. |

### Architecture

| Decision | Value |
|---|---|
| Entry point | Claude Code skill (`skill.md`). NOT a user-facing CLI. |
| Internal helpers | Python scripts under `agent-weiss/lib/` for hashing, state I/O, dispatch. Not user-facing. |
| Vocabulary | `profiles → domains → controls`. Composable profiles (multi-match per project). |
| Per-control artifacts | `prescribed.yaml` + `check.sh` (POSIX shell entry) + `policy.rego` + `policy_test.rego` + `instruct.md` |
| Bundle versioning | **Single bundle version**, no per-control semver. Defined in `bundle.yaml`. |
| Drift detection | Per-file `sha256` recorded in state file at last sync. Compared against bundle's per-file index. |
| `check.sh` output contract | One JSON line on stdout: `{"status": "pass"\|"fail"\|"setup-unmet", "findings_count": N, "summary": "...", "install"?: "...", "details_path"?: "..."}`. Exit codes: 0/1/127. |

### Source classification (4 classes)

Source-of-truth is `prescribed_files` map in `.agent-weiss.yaml` (path + sha256). File headers are courtesy-only.

| Class | Detection |
|---|---|
| Prescribed (clean) | In `prescribed_files`, hash matches |
| Prescribed (locally modified) | In `prescribed_files`, hash mismatch |
| Custom | Not in `prescribed_files`, file exists |
| Override | Entry under `prescribed.<control>.overrides` |

### Workflow

| Decision | Value |
|---|---|
| User loop order | Detect → Reconcile → Match profiles → Setup → Verify → Score → Report → Update state |
| Setup-first | Setup phase MUST run before verify. No score on absent infrastructure. |
| Reconciliation | Self-healing on each run. No transactional/atomic writes. Per-anomaly user prompts. |
| Approval UX | Per-change default, batched by domain. Verbs: `approve all`, `approve <domain>`, `<numbers>`, `skip <numbers>`, `explain <N>`, `dry-run`, `cancel`. |
| Setup score formula | Per-control: 100 if satisfied or override-with-reason, else 0. Per-domain: average. Total: average of domains. **Re-evaluated each run, never cached.** |
| Quality score formula | Per-control: 100 if pass, 0 if fail, excluded if setup-unmet. Per-domain: average of measurable. Total: average of domains. |
| Override = pass | Deliberate override (with `reason` field) counts as 100 in Setup score. |
| Tool installation | Skill INSTRUCTS via `install` field; never auto-runs `brew/uv/pnpm/apt`. |
| Backups | Pre-write to `.agent-weiss/backups/<timestamp>/` for any overwritten file. |
| Dry-run | Writes plan to `.agent-weiss/dry-run-<timestamp>.md`, exits without applying. |

### Testing strategy

| Decision | Value |
|---|---|
| Per-control fixtures | `agent-weiss/fixtures/profiles/<profile>/<domain>/<control>/{pass,fail}/` |
| Test runner | pytest, walks fixture tree, asserts expected exit codes |
| Rego tests | Existing pattern from agent-harness — `policy_test.rego` siblings, run via `conftest verify` |

### Scope

| Decision | Value |
|---|---|
| v1 profiles | universal, python, typescript |
| v1 domains | docs, security, vcs, project-structure, quality, testing |
| v1 control count | ~30-40 (~20-30 ported from agent-harness, ~10 new) |
| Deferred to v2 | docker profile, agent-readiness-docs domain, hooks domain, ci-cd domain, mcp domain, custom-policy automated review, bundle remote-fetch, native Windows, score weighting config, third-party local profiles |

### Plan-writing reminders (from v3 spec reviewer)

These are guidance, not gates:
1. First plan task = lock `prescribed.yaml` + `bundle.yaml` schemas
2. Installer must set `AGENT_WEISS_BUNDLE` env var across all 3 channels
3. Carry Approval UX batching pattern into Reconcile prompts
4. When reclassifying prescribed → custom, emit breadcrumb to `custom_policies` (preserve former `bundle_path`)

---

## Plan sequence

| # | Plan | Status | File | Depends on |
|---|---|---|---|---|
| 1 | **Foundations (MVP)** | Done | `2026-04-14-agent-weiss-foundations.md` | — |
| 2 | Control Library Build-Out | Done | TBD | Plan 1 |
| 3 | Setup Workflow & Approval UX | Done | TBD | Plan 1 |
| 4 | Verify Workflow & Scoring | Done | TBD | Plan 1 |
| 5 | Distribution Packaging | Pending | TBD | Plans 1, 3, 4 |
| 6 | Drift Refresh & Bundle Updates | Pending | TBD | Plans 1, 3, 4, 5 |

### Plan 1: Foundations (MVP)

**Goal:** A working skeleton that proves the entire pattern end-to-end with ONE control.

**Deliverables:**
- `yoselabs/agent-weiss` repo created with project structure
- `prescribed.yaml` schema locked (with example)
- `bundle.yaml` schema locked (with example, including per-file SHA index)
- State file (`.agent-weiss.yaml`) read/write
- Bundle root resolution (env var + probe order)
- Reconciliation algorithm (orphans, ghosts, partial-write detection)
- `check.sh` output contract parser
- ONE complete control end-to-end: `universal/docs/agents-md-present` (Rego + check.sh + fixtures + instruct.md)
- Fixture testing infrastructure (pass/fail tree + pytest runner)
- `skill.md` scaffolding describing the basic flow

**Out of scope for Plan 1:** approval UX polish, full control library, distribution packaging, bundle remote-fetch, drift refresh UX.

### Plan 2: Control Library Build-Out

**Goal:** Migrate ~20-30 controls from agent-harness + add ~10 new controls.

**Deliverables:**
- Per agent-harness Rego policy: corresponding control in agent-weiss tree (with prescribed.yaml + check.sh + instruct.md + policy.rego + tests + fixtures)
- New universal docs/security controls
- New python quality/testing controls (ruff, ty, pytest, coverage)
- New typescript quality/testing controls (biome, vitest)

### Plan 3: Setup Workflow & Approval UX

**Goal:** Polish the user-facing setup phase per the Approval UX spec.

**Deliverables:**
- Per-change approval batched by domain
- Verb parser (`approve all`, `approve <domain>`, `<numbers>`, `skip`, `explain N`, `dry-run`, `cancel`)
- Diff preview generation
- Backup mechanism (pre-write to `.agent-weiss/backups/<timestamp>/`)
- Dry-run mode (writes report, exits)
- Dependency re-evaluation after declines
- Reconcile UX uses same batching pattern

### Plan 4: Verify Workflow & Scoring

**Goal:** Run controls, parse JSON output, compute scores, generate report.

**Deliverables:**
- `check.sh` execution dispatcher
- JSON parsing per output contract
- Setup score formula (binary per-control, average up)
- Quality score formula (excluding setup-unmet)
- Report formatter (the human-readable output shown in spec §7)

### Plan 5: Distribution Packaging

**Goal:** Ship via all 3 channels with shared bundle.

**Deliverables:**
- Claude Code plugin manifest (`.claude-plugin/plugin.json`)
- PyPI package setup (pyproject.toml + entry point that installs bundle to `<env>/share/agent-weiss/`)
- npm package setup (package.json + postinstall script)
- All three installers MUST set `AGENT_WEISS_BUNDLE`
- CI publish workflows (per agent-harness pattern)

### Plan 6: Drift Refresh & Bundle Updates

**Goal:** Returning-user UX when bundle has updates.

**Deliverables:**
- Drift detection algorithm (compare project's `bundle_version` to installed bundle's)
- Per-file refresh proposals (3 cases: clean/locally-modified/orphaned-prescribed)
- 3-way merge UX for prescribed-locally-modified
- Header consistency maintenance
- Breadcrumb writing on prescribed → custom reclassification

---

## Decision retention strategy

1. **Spec is canonical.** Any decision conflict → spec wins. If spec is wrong, revise spec first, then update this roadmap.
2. **This roadmap is the program-level memory.** Update after every plan completes (mark status, link new plans, add cross-cutting decisions that emerged).
3. **Each plan references this roadmap and the spec.** Never restate cross-cutting decisions inside individual plans — link to this document instead.
4. **K project P105** (`~/Documents/Knowledge/Projects/105-yoselabs/`) holds the user-side context (brand vision, competitive landscape, motivations).

---

## Cross-references

- **Spec:** `docs/superpowers/specs/2026-04-14-agent-weiss-design.md`
- **K project:** `~/Documents/Knowledge/Projects/105-yoselabs/readme.md` (P105 Yose Labs)
- **Predecessor source code:** `yoselabs/agent-harness` (Rego policies and conftest patterns to be ported)
