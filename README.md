<p align="center">
  <h1 align="center">Agent Harness</h1>
  <p align="center">
    <strong>Deterministic quality gates for AI-assisted development</strong>
  </p>
  <p align="center">
    36 rules &middot; 5 stacks &middot; <500ms &middot; Zero config
  </p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> &middot;
    <a href="#stacks">Stacks</a> &middot;
    <a href="#for-ai-agents">For AI Agents</a> &middot;
    <a href="#contributing">Contributing</a>
  </p>
</p>

---

AI agents generate code in loops. Each iteration can introduce misconfigurations, missing healthchecks, bad Dockerfile layering, or secrets in git — and the agent won't know unless something tells it.

**Agent Harness is that something.** One CLI that detects your project stack, runs all quality checks, and gives agents actionable error messages they can fix without human intervention.

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

## Why

Agents need tight feedback loops. The tighter and more deterministic the feedback, the more effective the agent.

| Without harness | With harness |
|---|---|
| Agent commits `.env` with real secrets | `.gitignore` policy catches it before commit |
| Dockerfile rebuilds all deps every push | Layer ordering policy enforces correct `COPY` order |
| `pytest.mark.untit` silently selects nothing | Strict markers policy catches the typo |
| Compose healthcheck missing, deploy "succeeds" | Healthcheck policy fails the lint |
| Agent reformats code differently each iteration | Formatter runs on every check, enforcing consistency |

An agent can't act on *"consider using healthchecks."* It can act on *"FAIL: services.api missing healthcheck — add `healthcheck:` block."* That's the difference between documentation and a harness.

## Quick Start

```bash
# Install
uv tool install agent-harness   # or: pip install agent-harness

# See what's missing
agent-harness audit

# Set up configs
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
| **conftest** | Layer ordering, cache mounts, USER directive, HEALTHCHECK, secrets in ENV/ARG, base image pinning |
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

## Commands

| Command | Description |
|---------|-------------|
| `agent-harness detect` | Show detected stacks and subprojects |
| `agent-harness init` | Scaffold configs, Makefile, show tool availability (`--yes` for CI) |
| `agent-harness lint` | Run all checks — exits non-zero on failure (`--all` for monorepo) |
| `agent-harness fix` | Auto-fix (ruff, biome), then lint (`--all` for monorepo) |

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

**Current:** 36 Rego policies, 5 stacks (Python, JavaScript, Docker, Dokploy, Universal), 69 Python tests, 87 Rego tests.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

Every Rego policy follows the WHAT/WHY/WITHOUT IT/FIX pattern. Every Python check has a self-documenting docstring. Adding a rule? Write the WHY first — if you can't articulate why an AI agent needs this specific check, it doesn't belong here.

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  <sub>Built by <a href="https://github.com/iorlas">Denis Tomilin</a> at <a href="https://github.com/agentic-eng">Agentic Engineering</a></sub>
</p>
