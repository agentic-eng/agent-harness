# Agent Harness — harness engineering for AI agents

Single CLI that detects project stacks, runs all quality checks, audits harness completeness, and initializes new projects. Your Makefile delegates to it — `make lint` calls `agent-harness lint`.

## The problem

AI agents generate code in loops. Without deterministic controls, each loop can introduce new problems — misconfigurations, missing healthchecks, bad Dockerfile layering, secrets in git. The agent doesn't know it broke something unless something tells it.

Agents need tight feedback loops: write code, harness catches errors, agent reads errors, agent fixes. The tighter and more deterministic the feedback, the more effective the agent. That's what this tool provides.

## Quick start

```bash
# Install
uv tool install agent-harness  # or: pip install agent-harness

# Audit your project
agent-harness audit

# Initialize harness
agent-harness init

# Run all checks (<1s)
agent-harness lint

# Auto-fix then lint
agent-harness fix
```

## What's inside

34 Rego policies across 4 categories, plus external tool orchestration.

**Dockerfile** (7 rules) — layer ordering, cache mount usage, Alpine/musl detection, USER directive, HEALTHCHECK, secrets in ENV/ARG, base image pinning.

**Docker Compose** (12 rules) — build directives in prod, image pinning, implicit `:latest`, healthchecks on long-running services, restart policies, port binding, `$$` escaping, hostname configuration, bind mount volumes, inline config content.

**Python / pyproject.toml** (14 rules) — ruff output-format and line-length, coverage thresholds, pytest configuration, test isolation (no hardcoded paths, no `sleep` in tests).

**.gitignore** (1 rule) — secrets and artifacts (`.env`, `.venv`, `__pycache__`).

## Tool stack

Agent Harness orchestrates external tools — it doesn't embed them:

- **conftest** — runs the bundled Rego policies against project files
- **hadolint** — Dockerfile linting (DL/SC rules)
- **yamllint** — YAML syntax and style
- **ruff** — Python linting and formatting
- **ty** — Python type checking

If ruff, ty, or yamllint aren't globally installed, agent-harness falls back to `uv run` to invoke them.

## Requirements

- Python 3.12+
- conftest (required)
- hadolint (required for Docker projects)
- ruff, ty, yamllint — used via `uv run` fallback if not globally installed

## Configuration

Place a `.agent-harness.yml` in your project root. If absent, stacks are auto-detected from file presence.

```yaml
stacks:
  - python
  - docker

python:
  coverage_threshold: 95
  line_length: 140
  max_file_lines: 500

docker:
  own_image_prefix: "myorg/"
```

## Commands

| Command | Description |
|---------|-------------|
| `detect` | Detect project stacks (Python, Docker, etc.) |
| `lint` | Run all harness checks — exits non-zero on failure |
| `fix` | Auto-fix what's fixable (ruff format/fix), then lint |
| `init` | Scaffold harness config files onto a project |
| `audit` | Audit harness completeness — shows what's missing and how to fix it |

## For AI agents: how to use this

Every Rego policy file contains a structured comment block:

```
# WHAT: What this rule checks
# WHY: Why it matters for AI agents
# WITHOUT IT: What breaks in practice
# FIX: How to resolve the violation
```

### The agent workflow

1. **On lint failure:** `agent-harness lint` reports which rules failed with actionable messages.
2. **Agent fixes automatically** — most failures have clear fixes (add USER, add healthcheck, set output-format).
3. **If the user challenges a rule** ("ignore that, it doesn't apply"): read the WHY block from the `.rego` file and explain it to the user before suppressing. The WHY is the agent's argument.
4. **If the user still wants to suppress:** that's their call, but the agent informed them of the risk.

### Never ignore silently

When a check fails, agents should:
- Read the error message (it's actionable — "add healthcheck", "set output-format to concise")
- Fix it
- If unsure, read the `.rego` file's WHY block for context
- If the user says "skip it," cite the WHY and WITHOUT IT before proceeding

The policies exist because agents make these specific mistakes. The WHY explains which mistake and what breaks.

## What is a harness?

A harness is a **deterministic control** that constrains AI agent behavior automatically. Linters, type checkers, formatters, coverage gates, pre-commit hooks, CI checks — tools that run the same way every time and produce the same verdict for the same input.

A harness is NOT:
- Deployment conventions (healthchecks, restart policies, port bindings)
- Documentation (README, architecture docs)
- Agent configuration (MCP servers, .env files)
- Infrastructure (networking, DNS, orchestration)

**The test:** if a tool runs, analyzes code or config, and produces a pass/fail verdict without human judgment — it's a harness. If it requires interpretation or is a convention humans follow — it's not.

**Why harnesses matter for AI agents:** Agents generate code in loops. Without deterministic controls, each loop iteration may introduce new problems or fix one thing while breaking another. Harnesses create a closed feedback loop: agent writes code → harness catches errors → agent reads errors → agent fixes. The tighter and more deterministic this loop, the more effective the agent.

### Architecture

The harness is layered. Each layer composes on top of the previous:

```
┌─────────────────────────────────────┐
│  Framework (Django, FastAPI, Next.js)│  ← future
├─────────────────────────────────────┤
│  Stack (Python, JS/TS, Go)          │  ← stacks/python, stacks/js, ...
├─────────────────────────────────────┤
│  Infrastructure (Docker)            │  ← stacks/docker
├─────────────────────────────────────┤
│  Universal                          │  ← always applies
└─────────────────────────────────────┘
```

**Universal** applies to every project. Stack and infrastructure modules activate based on what the project uses. Framework modules (future) add framework-specific constraints on top of their stack.

An agent can't act on "consider using healthchecks." It can act on "FAIL: services.api missing healthcheck — add `healthcheck:` block." That's the difference between documentation and a harness.

## Status

MVP (v0.1) — actively developed. See [PLANS.md](PLANS.md) for roadmap.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
