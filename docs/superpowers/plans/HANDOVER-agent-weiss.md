# Handover — agent-weiss Plan 1 Execution

**Date:** 2026-04-14
**From:** Design + planning session
**To:** Implementation session

---

## What's done

1. **Spec** approved (4 review rounds): `docs/superpowers/specs/2026-04-14-agent-weiss-design.md`
2. **Roadmap** with cross-cutting decisions + 6-plan sequence: `docs/superpowers/plans/2026-04-14-agent-weiss-roadmap.md`
3. **Plan 1 (Foundations / MVP)** detailed and review-validated: `docs/superpowers/plans/2026-04-14-agent-weiss-foundations.md`
4. **K project** P105 Yose Labs: `~/Documents/Knowledge/Projects/105-yoselabs/readme.md`

## What's next

Execute Plan 1 (13 tasks, ~70 steps). Output: working `yoselabs/agent-weiss` repo with one end-to-end control proving the entire pattern.

---

## Recommended execution prompt for the new session

Open a new Claude Code session and paste this:

```
I'm continuing work on the agent-weiss project. The design is complete and Plan 1
(Foundations MVP) is ready to execute.

Read these files first, in order:
1. /Users/iorlas/Workspaces/agent-harness/docs/superpowers/plans/HANDOVER-agent-weiss.md
2. /Users/iorlas/Workspaces/agent-harness/docs/superpowers/plans/2026-04-14-agent-weiss-roadmap.md
3. /Users/iorlas/Workspaces/agent-harness/docs/superpowers/plans/2026-04-14-agent-weiss-foundations.md
4. /Users/iorlas/Documents/Knowledge/Projects/105-yoselabs/readme.md

Then execute Plan 1 using the superpowers:subagent-driven-development skill.
Dispatch a fresh subagent per task. Review between tasks. Mandatory:

- Honor every cross-cutting decision in the roadmap. Do not renegotiate.
- Follow TDD strictly per the plan (test fails first → implement → test passes → commit).
- The agent-weiss repo does NOT yet exist. Task 0 creates it at github.com/yoselabs/agent-weiss
  and clones to /Users/iorlas/Workspaces/agent-weiss.
- The roadmap and spec stay in /Users/iorlas/Workspaces/agent-harness — do not move them.
- Run superpowers:requesting-code-review after each task to catch issues early.
- After Plan 1 is complete (CI green, all tasks committed), update the roadmap status
  and stop. Do NOT auto-proceed to Plan 2 — confirm with the user first.

Start by acknowledging the read of all 4 files and confirming you understand the
scope (Plan 1 only, working skeleton + ONE end-to-end control), then ask the user
to confirm before invoking the subagent-driven-development skill.
```

---

## Critical context for the executing session

### Conventions to honor (from roadmap §1)

- **Identity:** `yoselabs/agent-weiss` org and repo. State file = `.agent-weiss.yaml`. Bundle env var = `AGENT_WEISS_BUNDLE`.
- **Platform:** POSIX/macOS/Linux/WSL only. Native Windows out of scope.
- **Vocabulary:** profiles → domains → controls. Composable profiles.
- **Per-control artifacts:** `prescribed.yaml + check.sh + policy.rego(+_test.rego) + instruct.md`.
- **Single bundle version** in `bundle.yaml`. No per-control semver.
- **`check.sh` output contract:** one JSON line on stdout, exit codes 0/1/127.
- **Source-of-truth for prescribed-vs-custom:** `.agent-weiss.yaml` `prescribed_files` map (path + sha256). Headers are courtesy only.
- **No CLI** — entry point is the Claude Code skill. Internal Python helpers only.

### Decisions to NOT relitigate

These were locked over multiple review rounds. The product name (`agent-weiss`), the org (`yoselabs`), the architecture (skill + bundle + Python helpers), the distribution (Claude marketplace + PyPI + npm mirrors), the source classification model, the two-score formula, the workflow order. Do not propose alternatives.

### Plan 1 scope guards

In scope: repo creation, schemas (prescribed.yaml + bundle.yaml), state I/O, bundle resolution, contract parser, reconciliation detector, ONE end-to-end control (universal/docs/agents-md-present), fixture testing, skill.md scaffold, CI.

Out of scope (named later plans): full control library (Plan 2), approval UX (Plan 3), scoring + report (Plan 4), distribution packaging (Plan 5), drift refresh UX (Plan 6).

If a subagent proposes work outside Plan 1's scope, redirect to "this is Plan N — defer."

---

## Decision retention check

If something feels under-specified during execution, the resolution order is:

1. **Plan 1 itself** (`docs/superpowers/plans/2026-04-14-agent-weiss-foundations.md`) — has explicit code/commands
2. **Roadmap** (`docs/superpowers/plans/2026-04-14-agent-weiss-roadmap.md`) — cross-cutting decisions
3. **Spec** (`docs/superpowers/specs/2026-04-14-agent-weiss-design.md`) — full design rationale
4. **Ask the user** — only when 1-3 don't resolve

Do not invent answers. Do not make architectural decisions without spec backing.

---

## Known risks (from third-pass spec review + plan review)

- **Bundle resolution probe paths** will diverge from real install paths once Plan 5 ships. Plan 1 tests use injected probe paths to avoid coupling.
- **ruamel.yaml round-trip** preservation is subtle. Plan 1 includes a forward-compat test for unknown keys; comment preservation is acknowledged-but-not-fully-tested.
- **skill.md is scaffold only.** Plans 3-4 will flesh out the actual user loop logic. Plan 1's skill.md is a contract preview, not a runnable behavior.
- **CI will need conftest** by Plan 2. Plan 1's CI installs it proactively to avoid surprise breaks.

---

## Status of supporting infrastructure

| Asset | Status |
|---|---|
| `yoselabs` GitHub org | Created (10 repos already migrated from agentic-eng) |
| `yoselabs/agent-weiss` repo | NOT yet created — Task 0 creates it |
| `yoselabs/agent-harness` repo | Live, deprecated-but-kept (legacy) |
| Local clone path for new repo | `/Users/iorlas/Workspaces/agent-weiss/` (will be created in Task 0) |
| Spec / roadmap / plans home | Stays in `/Users/iorlas/Workspaces/agent-harness/docs/superpowers/` |
| K project | P105 Yose Labs at `~/Documents/Knowledge/Projects/105-yoselabs/` |

---

## After Plan 1 completes

1. Mark roadmap Plan 1 → Done (Task 13 step 2)
2. Stop. Confirm with user before starting Plan 2.
3. Plan 2 (Control Library Build-Out) is the natural next step — migrates ~20-30 Rego policies from agent-harness and adds ~10 new controls.

The plan-writing skill should be re-invoked at that time with: "Write Plan 2 for agent-weiss based on the spec + roadmap. Plan 2 scope: migrate ~20-30 Rego policies from yoselabs/agent-harness and add ~10 new controls. Each control follows the pattern established by universal.docs.agents-md-present in Plan 1."
