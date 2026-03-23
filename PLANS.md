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
- Tested on real JS project (iorlas.com Astro blog), 60 Python tests + 73 Rego tests

## Next (v0.2)

- Publish to PyPI as `agent-harness`
- Publish policies as conftest OCI bundle (`conftest pull`)
- GitHub Actions workflow validation policies
- `.pre-commit-config.yaml` validation policies
- Parallel check execution (`concurrent.futures`)
- `audit` output as structured JSON (for agent consumption)
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
