# Contributing to Agent Harness

PRs welcome. File issues for bugs, feature requests, or new policy ideas.

## Development setup

```bash
git clone https://github.com/agentic-eng/agent-harness
cd agent-harness
uv sync
uv run pytest tests/ -v
uv run agent-harness --help
```

## Adding a new Rego policy

This is the most common contribution type. One file per concern, one concern per file.

### 1. Decide: is it deterministic?

The harness only contains deterministic controls — tools that produce a pass/fail verdict without human judgment. If a rule requires interpretation, it's guidance (document it in prose), not a policy.

### 2. Choose the right directory

- `policies/dockerfile/` — Dockerfile rules
- `policies/compose/` — Docker Compose rules
- `policies/python/` — pyproject.toml / Python config rules
- `policies/gitignore/` — .gitignore rules

### 3. Write the .rego file

Package name must match the directory structure:

```rego
package dockerfile.my_concern

# One-line description of what this policy enforces.
# Why this matters for AI agents.
#
# Input: <describe the parsed data structure>

import rego.v1

deny contains msg if {
    # your logic here
    msg := "Actionable error message — what's wrong and how to fix it"
}
```

**Conventions:**
- One file per concern (e.g., `layers.rego`, `cache.rego`, not `all_dockerfile_rules.rego`)
- Package name matches directory + filename: `policies/dockerfile/layers.rego` -> `package dockerfile.layers`
- Use `deny` for errors, `warn` for recommendations
- Error messages must be actionable — tell the agent what to do, not just what's wrong
- Comment at the top: what it checks, why, and the input structure

### 4. Write test fixtures (mandatory)

Every policy must have at least:
- One `bad_*` fixture that triggers the deny
- One `good_*` fixture that passes clean

Name fixtures descriptively: `bad_copy_before_deps.Dockerfile`, `good_layer_order.Dockerfile`.

Place in `tests/fixtures/<directory>/` (e.g., `tests/fixtures/dockerfile/`).

**Bad fixtures should ONLY fail on the rule being tested.** Include USER, HEALTHCHECK, cache mount, etc. in bad fixtures so they don't trigger unrelated rules.

### 5. Verify

```bash
# Run all Dockerfile fixture tests
conftest test tests/fixtures/dockerfile/*.Dockerfile --parser dockerfile -p policies/dockerfile/ --all-namespaces

# Run all Compose fixture tests
conftest test tests/fixtures/compose/*.yml -p policies/compose/ --all-namespaces

# Python/TOML example
conftest test tests/fixtures/python/bad_pyproject.toml \
  --parser toml \
  -p policies/python/ \
  --all-namespaces
```

Every `bad_*` must fail. Every `good_*` must pass. No exceptions.

### 6. Wire into the check module

If your policy targets a new file type, add it. Existing file types (Dockerfile, docker-compose.prod.yml, pyproject.toml, .gitignore) are already wired.

### 7. Update README.md

Update the rule count if you added new deny rules.

## Adding a new check module

Create a new file in `src/ai_harness/checks/`. Follow the existing pattern:

- Function takes `project_dir: Path` and returns `CheckResult`
- Use `run_check()` from `ai_harness.runner` for subprocess execution
- Add the call to `run_lint()` in `src/ai_harness/lint.py`

Look at `src/ai_harness/checks/hadolint.py` or `src/ai_harness/checks/ruff.py` for reference.

## Evaluating community rules

Before writing a custom Rego rule, check if an existing tool or community policy covers it.

### Checklist

1. **Does hadolint cover it?** (Dockerfile shell practices) -> Don't duplicate
2. **Does ruff cover it?** (Python code patterns) -> Don't duplicate
3. **Does yamllint cover it?** (YAML syntax) -> Don't duplicate
4. **Does a conftest community policy exist?** -> Evaluate for adoption
5. **Does Trivy's built-in check cover it?** -> Note the DS-* ID, write our own (Trivy is too slow for lint)

If an existing tool already enforces the rule, don't duplicate it in Rego. Write Rego policies for things no existing tool covers — structural requirements, cross-field validation, project-level configuration checks.

### Adoption criteria

| Criterion | Requirement |
|---|---|
| Maintained? | Last commit < 6 months ago |
| Actively used? | > 200 GitHub stars OR backed by an org |
| Correct for our use case? | Doesn't produce false positives for AI agent workflows |
| Worth the dependency? | If it's one rule, write our own. If it's a pack, consider importing. |

### When NOT to write a rule

- **It requires file existence checks** — conftest parses content, not filesystem. Use shell in Makefile.
- **It requires cross-file analysis** — conftest checks one file at a time. Use a shell script.
- **It's a judgment call** — document as guidance, not as a Rego policy.
- **An existing tool does it better** — hadolint, ruff, yamllint already have years of battle-tested rules.

## Tool stack

These tools are the harness foundation. Don't add new tools without justification.

| Tool | Purpose | Why this one |
|---|---|---|
| conftest | Custom Rego policies for any config file | Only tool that parses TOML + Dockerfile + YAML + JSON + .gitignore |
| hadolint | Dockerfile shell best practices | 12K stars, maintained, comprehensive built-in rules |
| yamllint | YAML syntax + duplicate key detection | Catches duplicate keys that conftest's parser silently merges |
| ruff | Python lint + format | 46K stars, fastest Python linter, comprehensive rules |
| check-jsonschema | Schema validation (compose, GitHub Actions) | Built-in schemas for CI/CD config files |

**Rejected tools and why:**
- **Trivy** — too slow for lint (~1s vs conftest's ~0.06s). Use for CI-only security scans if needed.
- **Dockle** — scans built images, not source files. Last commit 14 months ago.
- **DCLint** — Docker Compose linter, stalling (6 months no real commits), 255 stars.
- **CodeQL** — source code ASTs only, no config file support.

## Testing

```bash
uv run pytest tests/ -v
```

All tests must pass before submitting a PR.

## Code style

Follow existing patterns. Use ruff for formatting:

```bash
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/
```
