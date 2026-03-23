# TODO

Open questions and unchallenged assumptions from the initial build session.

## Unchallenged assumptions

- **500-line file limit.** Why 500? No data. Could be 300 (tighter) or 800 (more permissive). Need to test on real projects and see where false positives start.
- **"concise" ruff output is better for agents.** Assumed but not measured. Could test: give an agent the same lint errors in concise vs default format, measure fix success rate.
- **conftest as a runtime dependency.** Every project needs a Go binary installed. Is that a reasonable ask? Could we vendor it, bundle it, or make it optional (degrade gracefully)?

## Architecture

- **JSONC support for conftest.** `tsconfig.json`, `jsconfig.json`, `.vscode/*.json` use JSONC (comments + trailing commas). conftest's JSON parser chokes on these. Options: (a) strip comments before feeding to conftest, (b) write tsconfig checks in Python instead of Rego, (c) use check-jsonschema which handles JSONC natively. For now, skip known JSONC files in conftest-json check.
- **`audit --json`** — agents parse structured data better than prose. Priority for v0.2.
- **Auto-fix for Rego violations.** Ruff can auto-fix. Conftest can only report. When a Rego policy fails, could we provide fixers? E.g., "add USER nonroot" to Dockerfile, "add healthcheck block" to compose.
- **`agent-harness test`** — should it exist? Currently out of scope (Makefile owns `make test`). But if agent-harness owns lint and fix, should it also own test orchestration?
- **Pre-commit without pre-commit.** If agent-harness IS the lint tool, a raw git hook (`#!/bin/sh\nagent-harness lint`) works without the pre-commit framework. Simpler?
- **Parallel check execution.** Currently sequential. `concurrent.futures` could run independent checks in parallel. Measure first — is 749ms even worth optimizing?

## Distribution

- **Publish policies as conftest OCI bundle.** `conftest pull oci://ghcr.io/agentic-eng/agent-harness-policies:v1`. For projects that want policies without the CLI.
- **Marketplace agent skill.** Distribute as a Claude Code / Cursor skill that wraps agent-harness.
- **PyPI publish.** Reserve `agent-harness` name. Reclaim `agent-harness` via PEP 541 (abandoned since Sep 2023).

## Rules to investigate

- **GitHub Actions workflow policies.** Pinned action SHAs, permissions block, make targets in CI.
- **`.pre-commit-config.yaml` policies.** Local-only hooks, fix-before-lint order.
- **check-jsonschema integration.** Compose schema + GitHub Actions schema validation via built-in schemas.
