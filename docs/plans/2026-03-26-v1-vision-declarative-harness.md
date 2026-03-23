# v1.0 Vision: Declarative Harness Framework

> **Status:** Vision document. Not planned for immediate implementation. Guides architectural decisions.

## The Problem

Agent-harness currently wraps tools (ruff, biome, hadolint) with Python check modules. When tools evolve (Biome 2.x removed `--check`, ruff changes output formats), our wrappers break. This is the pre-commit / LangChain trap: thin wrappers become unmaintainable when the underlying tools evolve faster than the wrapper.

## The Vision

Agent-harness becomes a **declarative harness framework** — not a tool wrapper but a runner + policy library.

### What we ship:
1. **Runner** — reads config, runs declared commands, applies Rego policies, reports results
2. **Policy library** — Rego rules with WHY blocks (the valuable knowledge)
3. **Opinionated presets** — "here's what a Python+Docker project should look like"
4. **The skill** — agents learn how to use it and extend it

### What users declare:

```yaml
# .agent-harness.yml — purely declarative
tools:
  ruff:
    check: ruff check
    format: ruff format --check
    fix: ruff check --fix && ruff format
    detect: pyproject.toml

  biome:
    check: biome lint . && biome format .
    fix: biome check --fix .
    detect: package.json

policies:
  - source: bundled
    include: [dockerfile/*, compose/*, python/*]
    ignore: [compose.volumes]  # override: we use bind mounts

  - source: local
    path: .harness/policies/
```

### init as upgrade path

`init` is not just "set up from scratch" — it diffs current state against recommended state:

- Critical (deny rules): must fix, blocks lint
- Recommendations (warn rules): nice to have
- New rules available: from updated presets
- Deprecated: rules removed or replaced

Users run `init` periodically to see what's new. No version tracking — just current state vs. best practices.

### Local overrides

- Ignore specific rules: `ignore: [compose.volumes]`
- Add custom Rego policies: `source: local, path: .harness/policies/`
- Override tool commands: change one line in YAML when CLI flags change
- Fork presets: start from ours, customize per project

## Why Not Build This Now

The current Stack interface restructure is the right step. It:
- Makes each stack self-contained (prerequisite for presets)
- Extracts shared conftest runner (prerequisite for policy management)
- Separates detection from execution (prerequisite for declarative config)

The declarative model is the destination. The Stack interface is the path.

## What Gets Stale (And What Doesn't)

| Component | Stale risk | Mitigation |
|-----------|-----------|------------|
| Rego policies | Low — Docker healthchecks, .gitignore rules don't change | Knowledge, not wrappers |
| Tool commands | High — CLI flags change between versions | Declared in YAML, user overrides |
| Check modules (current) | High — Python wrappers around tool CLIs | Eliminated in declarative model |
| Presets | Medium — new tools emerge, best practices shift | `init` shows diff, easy to update |

## Inspiration

- **conftest** — policy engine, bring your own policies
- **ESLint flat config** — declarative, composable rule sets
- **Trunk** — opinionated defaults with per-project overrides
- **Nix** — declarative system configuration
