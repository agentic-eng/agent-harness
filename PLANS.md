# Roadmap

## Done (v0.1 — MVP)

- CLI commands: detect, lint, fix, init, audit
- 32 Rego policies across Dockerfile, Compose, Python, .gitignore
- Stack detection from file presence (Python, Docker)
- `.agent-harness.yml` config with auto-detection fallback
- Tool fallback — `uv run ruff`/`ty` when not in PATH
- JSON file validation via conftest parse
- Tested on real project (aggre), <1s execution

## Done (v0.1.1 — JS stack + universal fixes)

- **JavaScript/TypeScript stack** — Biome lint+format, framework-aware type checking (astro check > next lint > tsc), package.json Rego policies (engines, type:module, no wildcards)
- **File exclusion system** — `exclude:` in config + built-in defaults (lock files, build output, node_modules, archives). Wired into yamllint, conftest-json, file-length.
- **Stack-conditional gitignore** — .env universal, .venv/__pycache__ Python-only, node_modules/dist JS-only. No more false positives on wrong stacks.
- **JSONC skipping** — tsconfig.json, jsconfig.json, .vscode/ skipped by conftest-json
- **Extension-aware file length** — .py/.ts/.js: 500, .astro/.vue/.svelte: 800. Moved from Python-only to universal.
- **Biome VCS integration** — respects .gitignore via --vcs-enabled, skips dist/, .astro/, node_modules/
- **Dokploy stack** — auto-detection from `dokploy-network` in compose files, 2 Rego policies (traefik.enable required, dokploy-network required for Traefik-routed services)
- Tested on real JS project (iorlas.com Astro blog), 60 Python tests + 73 Rego tests

## Next (v0.2 — CLI simplification + monorepo)

- **CLI: 4 commands** — detect, init, lint, fix. Remove `audit` (absorbed by detect + init).
- **Monorepo support** — distributed dotfiles, `detect` scans subdirectories, `lint --all` runs all scopes in parallel
- **Makefile scaffolding** — `init` creates Makefile with `make lint` target
- **Init confirmation** — shows detected stacks + tool descriptions, `--yes` for CI/agents
- See `docs/plans/2026-03-26-v02-cli-simplification.md` for full plan

### Also v0.2
- Publish to PyPI as `agent-harness`
- GitHub Actions workflow validation policies
- `.pre-commit-config.yaml` validation policies
- Dockerfile secrets check: detect hardcoded values, not just suspicious key names

## Future (v0.3+)

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
