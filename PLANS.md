# Roadmap

## Done (v0.1 — MVP)

- CLI commands: detect, lint, fix, init, audit
- 32 Rego policies across Dockerfile, Compose, Python, .gitignore
- Stack detection from file presence (Python, Docker)
- `.harness.yml` config with auto-detection fallback
- Tool fallback — `uv run ruff`/`ty` when not in PATH
- JSON file validation via conftest parse
- Tested on real project (aggre), <1s execution

## Next (v0.2)

- Publish to PyPI as `agent-harness`
- Publish policies as conftest OCI bundle (`conftest pull`)
- GitHub Actions workflow validation policies
- `.pre-commit-config.yaml` validation policies
- Parallel check execution (`concurrent.futures`)
- `audit` output as structured JSON (for agent consumption)
- Dockerfile secrets check: detect hardcoded values, not just suspicious key names

## Future (v0.3+)

- JavaScript/TypeScript stack module (eslint, prettier, vitest, tsc)
- Go stack module (golangci-lint, go test, go vet)
- `agent-harness upgrade` — pull latest policies without reinstalling
- Policy bundle versioning — pin and bump policy versions per project
- Config generation — `init` generates pyproject.toml ruff/coverage/pytest sections
- CLAUDE.md / AGENTS.md generation — `init` creates agent context file
- check-jsonschema integration (Compose schema, GitHub Actions schema validation)
- Makefile generation (for projects that still want make targets)

## Non-goals

- **Embedding tools** (ruff, hadolint, conftest) — always external dependencies
- **Running in Docker** — must be <1s local execution
- **Replacing CI** — CI runs the same `agent-harness lint`, but local-first
- **Being a general-purpose linter** — this is specifically for AI agent harness engineering
