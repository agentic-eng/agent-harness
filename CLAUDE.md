# agent-harness

Deterministic quality gates for AI-assisted development. This project IS a harness — it enforces its own rules.

## Dev Commands

```bash
make lint          # agent-harness lint (runs all checks)
make fix           # agent-harness fix (auto-fix, then lint)
make test          # pytest + conftest verify (all tests)
make audit         # agent-harness audit (gap analysis)
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
  cli.py              — Click CLI entry point
  config.py            — .agent-harness.yml parsing, HarnessConfig dataclass
  detect.py            — Stack detection orchestrator
  runner.py            — Subprocess execution, CheckResult dataclass
  exclusions.py        — File exclusion patterns (lock files, build output)
  lint.py              — Check pipeline (universal → per-stack)
  fix.py               — Auto-fix (ruff, biome)
  audit.py             — Gap analysis
  init/                — Scaffolding (config files, templates)
  stacks/
    universal/         — Always runs: yamllint, gitignore, JSON, file length
    python/            — ruff, ty, conftest on pyproject.toml
    javascript/        — Biome, framework type checker, conftest on package.json
    docker/            — hadolint, conftest on Dockerfile + compose
    dokploy/           — conftest for Traefik/Dokploy conventions

policies/              — Rego policies (conftest). Each has WHAT/WHY/FIX comments.
skills/agent-harness/  — Claude Code plugin (SKILL.md + guidance docs)
```

## Conventions

- One check per file, with WHAT/WHY/WITHOUT IT/FIX/REQUIRES docstring
- One Rego policy per file, with `_test.rego` sibling
- Tests use `tmp_path` fixtures, mock subprocesses via `monkeypatch`
- Tool fallback: `shutil.which()` → `uv run` (Python) or `npx` (JS)
- `import rego.v1` and `if` keyword required in all Rego files

## Never

- Never embed tool binaries — require them installed externally
- Never run checks in Docker — must be <500ms local
