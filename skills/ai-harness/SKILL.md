---
name: ai-harness
description: "Harness engineering for AI agents. Use when setting up a new project, auditing harness coverage, or when agent output is too noisy. Triggers: 'harness audit', 'check harness', 'apply harness', new project setup, first commit on a new repo."
---

# Agent Harness

Deterministic controls (linters, type checkers, formatters, coverage gates) that constrain AI agent behavior. Run `agent-harness lint` constantly — it's your feedback loop.

## Quick Start

```bash
# Install (one-time)
uv tool install agent-harness

# On any project:
agent-harness audit    # what's missing?
agent-harness init     # scaffold configs
agent-harness lint     # run all checks (<1s)
agent-harness fix      # auto-fix, then lint
```

## When to Use

- Setting up a new project for AI-assisted development
- Auditing an existing project's harness coverage
- Agent output is too noisy, errors aren't actionable, or the fix-verify loop is manual
- User says "harness audit", "check harness", "apply harness"

## When NOT to Use

- Business logic, architecture, or domain modeling
- Deployment conventions or infrastructure (use deployment-platform skill)
- General style questions (just answer directly)
- Fixing one specific tool config (help directly)

## Stacks

Agent-harness detects and enforces per stack:

| Stack | Detected by | Tools | Key rules |
|-------|------------|-------|-----------|
| **Python** | `pyproject.toml`, `setup.py` | ruff, ty, conftest | Strict markers, coverage >=90%, verbose output, line length |
| **JavaScript** | `package.json`, `tsconfig.json` | Biome, framework type checker | engines field, type:module, no wildcard versions |
| **Docker** | `Dockerfile`, `docker-compose*.yml` | hadolint, conftest | Layer ordering, cache mounts, USER, healthchecks, no bind mounts |
| **Dokploy** | `dokploy-network` in compose | conftest | traefik.enable required, dokploy-network for routed services |
| **Universal** | Always | yamllint, conftest | .gitignore entries (stack-aware), JSON validation, file length |

## Agent Workflow

1. **On lint failure:** `agent-harness lint` reports which rules failed with actionable messages.
2. **Fix automatically** — most failures have clear fixes. Run `agent-harness fix` for auto-fixable issues.
3. **If the user challenges a rule:** read the WHY block from the `.rego` policy file and explain it before suppressing.
4. **If the user still wants to suppress:** that's their call, but inform them of the risk.

## Guidance

When writing new Docker, compose, or Python code, read the guidance docs for recipes and patterns:

- **Docker** — `docs/guidance/docker.md`: healthcheck recipes (PostgreSQL, Redis, MySQL, HTTP, auth-protected, Alpine, distroless), dependency chains, migration patterns, config file strategy, base image selection
- **Python** — `docs/guidance/python.md`: why each pyproject.toml knob matters

These are non-deterministic best practices — judgment calls that can't be linted but help agents write correct code the first time.

## Policy WHY Blocks

Every Rego policy file contains a structured comment:

```
# WHAT: What this rule checks
# WHY: Why it matters for AI agents
# WITHOUT IT: What breaks in practice
# FIX: How to resolve the violation
```

When a user asks "why does this rule exist?" — read the policy file's WHY block. It's the agent's argument.
