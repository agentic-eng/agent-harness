# agent-harness

Deterministic quality gates for AI-assisted development. This project IS a harness — it enforces its own rules.

## Dev Commands

```bash
make lint          # agent-harness lint (runs all checks)
make fix           # agent-harness fix (auto-fix, then lint)
make test          # pytest + conftest verify (all tests)
```

Install dev deps: `uv sync`

## Setup

```bash
uv tool install -e .          # install CLI globally from source
uv sync                       # install dev deps (ruff, ty, pytest)
agent-harness lint             # verify everything passes
```

## Architecture

```
src/agent_harness/
  cli.py               — Click CLI: detect, init, lint, fix (thin — delegates)
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
  policies/            — Rego policies (bundled). Each has WHAT/WHY/FIX.

skills/agent-harness/  — Claude Code plugin (SKILL.md + guidance docs)
```

## Adding a new preset

1. Create `presets/<name>/` with `__init__.py` implementing `Preset`
2. Add individual check files (one per tool)
3. Add `<Name>Preset()` to `registry.py`
4. Add Rego policies to `policies/<name>/` if needed

## Conventions

- Each preset implements: `detect()`, `run_checks()`, `run_fix()`, `get_info()`
- One check per file, with WHAT/WHY/WITHOUT IT/FIX/REQUIRES docstring
- One Rego policy per file, with `_test.rego` sibling
- All conftest checks use shared `conftest.py` (never local `_run_conftest`)
- Tool fallback: `shutil.which()` → `uv run` (Python) or `npx` (JS)

## Never

- Never embed tool binaries — require them installed externally
- Never run checks in Docker — must be <500ms local
- Never duplicate `_run_conftest` — use `agent_harness.conftest.run_conftest()`
