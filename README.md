<p align="center">
  <h1 align="center">🦎 Agent Harness</h1>
  <p align="center">
    <em>Enforce. Enforce. Enforce.</em>
  </p>
  <p align="center">
    <strong>Stop the slop. AI agents aren't sloppy — the human toolchains they inherited are.</strong>
  </p>
  <p align="center">
    44 rules &middot; 5 stacks &middot; <500ms &middot; Zero config
  </p>
  <p align="center">
    <a href="https://pypi.org/project/agentic-harness/"><img src="https://img.shields.io/pypi/v/agentic-harness" alt="PyPI"></a>
    <a href="https://pypi.org/project/agentic-harness/"><img src="https://img.shields.io/pypi/dm/agentic-harness" alt="Downloads"></a>
    <a href="https://github.com/yoselabs/agent-harness/actions/workflows/ci.yml"><img src="https://github.com/yoselabs/agent-harness/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <a href="https://www.apache.org/licenses/LICENSE-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License: Apache 2.0"></a>
    <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.12%2B-blue.svg" alt="Python 3.12+"></a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet" alt="Built with Claude Code">
    <img src="https://img.shields.io/badge/Linted%20with-ruff-orange" alt="Linted with ruff">
    <img src="https://img.shields.io/badge/Policies-OPA%20%2F%20Rego-lightgrey" alt="Policies: OPA / Rego">
  </p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> &middot;
    <a href="#the-problem">The Problem</a> &middot;
    <a href="#stacks">Stacks</a> &middot;
    <a href="#for-ai-agents">For AI Agents</a> &middot;
    <a href="#contributing">Contributing</a>
  </p>
</p>

> **PyPI:** Install as `agentic-harness` — the `agent-harness` name is reserved by an unrelated abandoned package ([transfer pending](https://github.com/pypi/support/issues)). CLI command is `agent-harness`.

---

```
Agent: writes Dockerfile, commits
  ↓
agent-harness lint → FAIL: no USER directive, no HEALTHCHECK, COPY . . before pip install
  ↓
Agent: reads errors, fixes all three, re-lints
  ↓
agent-harness lint → 10 passed, 0 failed (476ms)
  ↓
Agent: commits clean code. No human involved.
```

Dockerfiles without USER directives. Compose files without healthchecks. Secrets hardcoded in ENV. Dependency caches busted on every build. Coverage gates that don't exist. Formatters that never run.

This isn't the AI's fault. These are **human-built toolchains with decades of accumulated slop** — implicit defaults, silent failures, missing guardrails. Humans learned to work around them through tribal knowledge. AI agents don't have tribal knowledge. They just hit the wall.

**Agent Harness is the wall that talks back.** One CLI, deterministic feedback, actionable error messages. Every rule exists because an AI agent made that exact mistake — and will keep making it until something stops it.

```
$ agent-harness lint

  PASS  conftest-gitignore (39ms)
  PASS  conftest-json (0ms)
  PASS  yamllint (117ms)
  PASS  file-length (0ms)
  PASS  ruff:format (50ms)
  PASS  ruff:check (118ms)
  PASS  ty (109ms)
  PASS  conftest-python (43ms)

8 passed, 0 failed (476ms)
```

## The Problem

AI agents are as good as the feedback they get. Human toolchains give terrible feedback — or none at all.

| The slop | What the agent does | What the harness does |
|---|---|---|
| `.gitignore` is "optional" | Commits `.env` with real secrets | Policy catches it before commit |
| Dockerfile layer order is tribal knowledge | `COPY . .` before `pip install` — 5min rebuilds | Layer ordering policy enforces correct order |
| `pytest.mark.untit` silently selects nothing | Thinks tests pass (zero ran) | Strict markers policy catches the typo |
| Compose healthcheck is "recommended" | Deploy "succeeds," service is dead | Healthcheck policy fails the lint |
| Formatters exist but nobody runs them | Reformats differently each iteration | Formatter runs on every commit, enforcing consistency |

An agent can't act on *"consider using healthchecks."* It can act on *"FAIL: services.api missing healthcheck — add `healthcheck:` block."*

That's the difference between documentation and a harness. Documentation hopes. A harness enforces.

> We'll build AI-first frameworks eventually. Until then, agents have to work with what humans built. Agent Harness makes that survivable.

## Quick Start

```bash
# Install
uv tool install agentic-harness   # or: pip install agentic-harness

# Detect stacks + subprojects
agent-harness detect

# Set up configs and Makefile
agent-harness init

# Run all checks
agent-harness lint

# Auto-fix what's fixable, then lint
agent-harness fix
```

## Stacks

Agent Harness auto-detects your project and activates the right checks. Zero config required.

### Python

Detected by `pyproject.toml`, `setup.py`, `requirements.txt`

| Tool | What it checks |
|------|---------------|
| **ruff** | Linting + formatting (fastest Python linter) |
| **ty** | Type checking |
| **conftest** | pytest strict-markers, coverage >=90%, verbose output, ruff config |
| **file-length** | No file exceeds 500 lines |

### JavaScript / TypeScript

Detected by `package.json`, `tsconfig.json`

| Tool | What it checks |
|------|---------------|
| **Biome** | Linting + formatting (single Rust-based tool, ~20x faster than ESLint) |
| **Framework type checker** | `astro check`, `next lint`, or `tsc --noEmit` — auto-detected |
| **conftest** | `engines` field, `type: "module"`, no wildcard `*` versions |

### Docker

Detected by `Dockerfile`, `docker-compose*.yml`

| Tool | What it checks |
|------|---------------|
| **hadolint** | Dockerfile best practices (DL/SC rules) |
| **conftest** | Layer ordering, cache mounts, USER directive, HEALTHCHECK, secrets in ENV/ARG, base image pinning (discovers all Dockerfiles in tree) |
| **conftest** (compose) | Healthchecks, restart policies, image pinning, port binding, `$$` escaping, no bind mounts, no inline configs |

### Dokploy

Detected by `dokploy-network` reference in compose files

| Tool | What it checks |
|------|---------------|
| **conftest** | `traefik.enable=true` on labeled services, `dokploy-network` for routed services |

### Universal

Always active on every project.

| Tool | What it checks |
|------|---------------|
| **yamllint** | YAML syntax, duplicate keys, truthy values |
| **conftest** | `.gitignore` completeness (stack-aware), JSON validity |
| **file-length** | Extension-aware: `.py`/`.ts` 500 lines, `.astro`/`.vue` 800 lines |

## Configuration

Zero config by default — stacks are auto-detected. Override with `.agent-harness.yml`:

```yaml
stacks:
  - python
  - docker
  - javascript

exclude:
  - _archive/
  - vendor/

python:
  coverage_threshold: 95
  line_length: 140
  max_file_lines: 500

javascript:
  coverage_threshold: 80

docker:
  own_image_prefix: "ghcr.io/myorg/"
```

### Conftest Exceptions

Skip individual policies per file when legitimate:

```yaml
docker:
  conftest_skip:
    scripts/autonomy/Dockerfile:
      - dockerfile.user        # runs as root intentionally
      - dockerfile.healthcheck # not a service
```

See [SKILL.md](skills/agent-harness/SKILL.md#conftest-exceptions) for the full list of exception IDs.

## Commands

| Command | Description |
|---------|-------------|
| `agent-harness detect` | Show detected stacks and subprojects |
| `agent-harness init` | Scaffold configs, Makefile, show tool availability |
| `agent-harness init --apply` | Apply auto-fixes and create missing config files |
| `agent-harness lint` | Run all checks — exits non-zero on failure |
| `agent-harness fix` | Auto-fix (ruff, biome), then lint |
| `agent-harness security-audit` | Scan working dir for vulnerable deps + leaked secrets |
| `agent-harness security-audit-history` | Deep scan full git history for leaked secrets |

## For AI Agents

### The feedback loop

```
Agent writes code
       ↓
agent-harness lint
       ↓
  ┌─ PASS → commit
  └─ FAIL → agent reads error → agent fixes → re-lint
```

Every error message is actionable. Every Rego policy has a structured comment:

```
# WHAT: What this rule checks
# WHY: Why it matters for AI agents
# WITHOUT IT: What breaks in practice
# FIX: How to resolve the violation
```

### When a user challenges a rule

1. Read the WHY block from the `.rego` file
2. Explain the risk to the user
3. If they still want to suppress — that's their call

The WHY exists because agents make these specific mistakes. It's the agent's argument.

### Claude Code plugin

Agent Harness ships as a Claude Code plugin with guidance docs:

```bash
# Load as plugin
claude --plugin-dir /path/to/agent-harness

# Or add to your shell alias
alias c="claude --plugin-dir ~/path/to/agent-harness"
```

The plugin includes:
- **Skill** — when to use, workflow, stack reference
- **Docker guidance** — healthcheck recipes, migration patterns, config strategies
- **Python guidance** — why each pyproject.toml knob matters

## Architecture

```
┌─────────────────────────────────────┐
│  Framework (Django, FastAPI, Next.js)│  ← future
├─────────────────────────────────────┤
│  Stack (Python, JS/TS, Go)          │
├─────────────────────────────────────┤
│  Infrastructure (Docker, Dokploy)   │
├─────────────────────────────────────┤
│  Universal                          │  ← always active
└─────────────────────────────────────┘
```

Each layer composes on top of the previous. Adding a new stack = creating a new directory. Each check is a self-contained file with its own docstring, test, and single responsibility.

## Tool Stack

Agent Harness orchestrates external tools — it doesn't embed them:

| Tool | Purpose | Fallback |
|------|---------|----------|
| [conftest](https://www.conftest.dev/) | Rego policy engine | Required |
| [hadolint](https://github.com/hadolint/hadolint) | Dockerfile linting | Required for Docker |
| [ruff](https://docs.astral.sh/ruff/) | Python linting + formatting | `uv run` fallback |
| [ty](https://docs.astral.sh/ty/) | Python type checking | `uv run` fallback |
| [Biome](https://biomejs.dev/) | JS/TS linting + formatting | `npx` fallback |
| [yamllint](https://github.com/adrienverge/yamllint) | YAML validation | `uv run` fallback |

## Requirements

- Python 3.12+
- [conftest](https://www.conftest.dev/install/) (required)
- [hadolint](https://github.com/hadolint/hadolint#install) (for Docker projects)
- Other tools auto-fallback via `uv run` or `npx`

## Status

Actively developed. See [PLANS.md](PLANS.md) for roadmap.

**Current:** 44 Rego deny rules, 5 stacks (Python, JavaScript, Docker, Dokploy, Universal), 201 Python tests, 109 Rego tests.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

Every Rego policy follows the WHAT/WHY/WITHOUT IT/FIX pattern. Every Python check has a self-documenting docstring. Adding a rule? Write the WHY first — if you can't articulate why an AI agent needs this specific check, it doesn't belong here.

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

<p align="center">
  <sub>🦎 Cold-blooded enforcement since mid 2025.</sub>
</p>
<p align="center">
  <sub>Built by <a href="https://github.com/iorlas">Denis Tomilin</a> at <a href="https://github.com/yoselabs">Yose Labs</a></sub>
</p>
