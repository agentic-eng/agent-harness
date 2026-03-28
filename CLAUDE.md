# agent-harness

Deterministic quality gates for AI-assisted development. This project IS a harness — it enforces its own rules.

## Dev Commands

```bash
make lint             # agent-harness lint (runs all checks)
make fix              # agent-harness fix (auto-fix, then lint)
make test             # pytest + conftest verify (all tests)
make security-audit                   # check deps + secrets in working dir (fast)
make check                            # full gate: lint + test + security-audit
agent-harness security-audit-history  # deep scan git history for leaked secrets (run once)
```

Install dev deps: `uv sync`

## Workflow

Pre-commit hooks run `agent-harness fix` and `agent-harness lint` automatically on every commit.
Before declaring work done, always run `make check` — it's the full quality gate.


## Setup

```bash
uv tool install -e .          # install CLI globally from source
uv sync                       # install dev deps (ruff, ty, pytest)
agent-harness lint             # verify everything passes
```

## Architecture

```
src/agent_harness/
  cli.py               — Click CLI: detect, init, lint, fix, security-audit (thin — delegates)
  config.py            — Dict-based config from .agent-harness.yml
  runner.py            — run_check(), CheckResult, tool_available()
  conftest.py          — Shared conftest runner (used by all Rego checks)
  exclusions.py        — File exclusion patterns
  workspace.py         — Discover subproject roots
  preset.py            — Preset base class + ToolInfo/PresetInfo
  registry.py          — Explicit preset registration (PRESETS + UNIVERSAL)
  detect.py            — Thin orchestrator: for preset in PRESETS: preset.detect()
  lint.py              — Thin orchestrator: for preset in PRESETS: preset.run_checks()
  fix.py               — Thin orchestrator: for preset in PRESETS: preset.run_fix()
  init/                — Scaffolding (reads preset.get_info())
  presets/
    universal/         — Always runs: yamllint, gitignore, JSON, file length
    python/            — ruff, ty, conftest on pyproject.toml
    javascript/        — Biome, framework type checker, conftest on package.json
    docker/            — hadolint, conftest on Dockerfile + compose
    dokploy/           — conftest for Traefik/Dokploy conventions
  security/            — osv-scanner + gitleaks runners, policy engine, CVE ignore
  policies/            — Rego policies (bundled). Each has WHAT/WHY/FIX.

skills/agent-harness/  — Claude Code plugin (SKILL.md + guidance docs)
```

## Adding a new preset

1. Create `presets/<name>/` with `__init__.py` implementing `Preset`
2. Add individual check files (one per tool)
3. Add `<Name>Preset()` to `registry.py`
4. Add Rego policies to `policies/<name>/` if needed

## Conventions

- Each preset implements: `detect()`, `run_checks()`, `run_fix()`, `run_setup()`, `get_info()`
- One check per file, with WHAT/WHY/WITHOUT IT/FIX/REQUIRES docstring
- One Rego policy per file, with `_test.rego` sibling
- All conftest checks use shared `conftest.py` (never local `_run_conftest`)
- Tool fallback: `shutil.which()` → `uv run` (Python) or `npx` (JS)

## Policy Design Strategy

Every check belongs in exactly one place. The boundary:

**"Would any reasonable person agree this is broken?"**
- YES → lint (Rego `deny` rule in `policies/`)
- Debatable → init (Python setup check in `presets/*/setup.py`)

### Lint (Rego, every commit)
- Only `deny` rules. No `warn`.
- Checks that gates EXIST and aren't objectively broken.
- Examples: `--strict-markers` missing, `--cov-fail-under` missing, threshold < 30%

### Init (Python, on-demand)
- `SetupIssue` with severity `critical` (fixable) or `recommendation`.
- Checks configuration QUALITY. Can auto-fix.
- Examples: threshold = 50% (recommend 90-95%), missing `-v` flag

### Skill (agent guidance, context-dependent)
- Actions that require judgment, context, or reading intent.
- The skill tells the agent WHAT to evaluate and WHY, but the agent decides HOW.
- Examples: reorganize .gitignore (needs to know which patterns are stale),
  audit CLAUDE.md (needs project context), replace redundant Makefile targets
  (needs to understand what the target was for)

### The boundary: init does, skill guides
Init must be safe to run blindly (`--apply` never breaks a project).
If an action could destroy user intent (rewriting .gitignore, editing CLAUDE.md),
init does the safe subset (deduplicated append) and the skill guides the agent
to do the rest (full cleanup, reorganization).

### Same topic, all three places
A single topic (e.g., .gitignore completeness) can have:
- Lint Rego: "are generated files tracked?" (objectively broken)
- Init Python: "append missing patterns grouped by category" (safe, mechanical)
- Skill: "review and clean up the full .gitignore — remove stale patterns, reorganize" (judgment)

## Never

- Never embed tool binaries — require them installed externally
- Never run checks in Docker — must be <500ms local
- Never duplicate `_run_conftest` — use `agent_harness.conftest.run_conftest()`
- Never truncate lint/test output with `| tail` or `| head` — output is already optimized
- Never skip `make check` before declaring a task complete
