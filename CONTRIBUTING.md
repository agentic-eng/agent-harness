# Contributing to Agent Harness

Agent Harness enforces its own rules. We use agent-harness to develop agent-harness.

## Development setup

```bash
git clone https://github.com/yoselabs/agent-harness
cd agent-harness
uv sync                          # install dev deps
uv tool install -e .             # install CLI globally from source
agent-harness lint               # verify everything passes
```

## Quality gate

Before every commit (enforced by pre-commit hooks):

```bash
make check                       # lint + test + security-audit
```

This runs:
- `agent-harness lint` — 10 checks (ruff, ty, conftest, yamllint, etc.)
- `uv run pytest tests/ -v` — 201 Python tests
- `conftest verify` — 109 Rego policy tests
- `agent-harness security-audit` — dependency + secret scanning

## Adding a new Rego policy

One file per concern, one concern per file.

### 1. Decide: is it deterministic?

The harness only contains deterministic controls — tools that produce a pass/fail verdict without human judgment. If a rule requires interpretation, it's guidance (document it in the skill), not a policy.

### 2. Choose the right directory

- `src/agent_harness/policies/dockerfile/` — Dockerfile rules
- `src/agent_harness/policies/compose/` — Docker Compose rules
- `src/agent_harness/policies/dokploy/` — Dokploy/Traefik rules
- `src/agent_harness/policies/python/` — pyproject.toml / Python config rules
- `src/agent_harness/policies/gitignore/` — .gitignore rules

### 3. Write the .rego file

```rego
package dockerfile.my_concern

# One-line description.
# Why this matters for AI agents.
#
# Input: <describe the parsed data structure>

import rego.v1

default _exceptions := []

_exceptions := data.exceptions if {
    data.exceptions
}

deny contains msg if {
    not "dockerfile.my_concern" in _exceptions
    # your logic here
    msg := "Actionable error message — what's wrong and how to fix it"
}
```

**Conventions:**
- One file per concern (e.g., `layers.rego`, `cache.rego`)
- Package name matches directory + filename: `policies/dockerfile/layers.rego` → `package dockerfile.layers`
- Only `deny` rules. No `warn`.
- Error messages must be actionable — tell the agent what to do
- WHAT/WHY/WITHOUT IT/FIX comment block at top
- Always include `_exceptions` guard so policies can be skipped via `conftest_skip`

### 4. Write the test file

Every policy needs a `_test.rego` sibling with at least:

```rego
package dockerfile.my_concern_test

import rego.v1
import data.dockerfile.my_concern

test_bad_input_fires if {
    my_concern.deny with input as [...]
}

test_good_input_passes if {
    count(my_concern.deny) == 0 with input as [...]
}

test_exception_skips if {
    count(my_concern.deny) == 0 with input as [...]
        with data.exceptions as ["dockerfile.my_concern"]
}
```

### 5. Write fixture files

Place in `tests/fixtures/<directory>/`:
- `bad_*.Dockerfile` — triggers the deny
- `good_*.Dockerfile` — passes clean

Bad fixtures should ONLY fail on the rule being tested. Include USER, HEALTHCHECK, cache mount, etc. so they don't trigger unrelated rules.

### 6. Verify

```bash
# Rego unit tests
conftest verify --policy src/agent_harness/policies/dockerfile/

# Fixture tests
conftest test tests/fixtures/dockerfile/*.Dockerfile \
  --parser dockerfile \
  -p src/agent_harness/policies/dockerfile/ \
  --all-namespaces

# Full quality gate
make check
```

### 7. Update exception ID table

Add the new exception ID to `skills/agent-harness/SKILL.md` in the Conftest Exceptions table.

## Adding a new preset

1. Create `presets/<name>/` with `__init__.py` implementing `Preset`
2. Add individual check files (one per tool, with WHAT/WHY/WITHOUT IT/FIX docstring)
3. Add `<Name>Preset()` to `registry.py`
4. Add Rego policies to `policies/<name>/` if needed
5. Run `make check`

## Adding a new check module

Create a new file in `src/agent_harness/presets/<stack>/`. Follow the existing pattern:

- Function takes `project_dir: Path` and returns `CheckResult` (or `list[CheckResult]`)
- Use `run_check()` from `agent_harness.runner` for subprocess execution
- Wire the call into the preset's `run_checks()` method

## Evaluating community rules

Before writing a custom Rego rule, check if an existing tool covers it:

1. **Does hadolint cover it?** (Dockerfile shell practices) → Don't duplicate
2. **Does ruff cover it?** (Python code patterns) → Don't duplicate
3. **Does yamllint cover it?** (YAML syntax) → Don't duplicate
4. **Does a conftest community policy exist?** → Evaluate for adoption
5. **Does Trivy's built-in check cover it?** → Note the DS-* ID, write our own (Trivy is too slow)

If an existing tool covers it, don't duplicate in Rego.

### When NOT to write a rule

- **It requires file existence checks** — conftest parses content, not filesystem
- **It requires cross-file analysis** — conftest checks one file at a time
- **It's a judgment call** — document as guidance in the skill, not as a Rego policy
- **An existing tool does it better** — hadolint, ruff, yamllint have years of battle-tested rules

## Tool stack

| Tool | Purpose | Why this one |
|------|---------|-------------|
| conftest | Rego policies for any config file | Only tool that parses TOML + Dockerfile + YAML + JSON + .gitignore |
| hadolint | Dockerfile shell best practices | 12K stars, maintained, comprehensive |
| yamllint | YAML syntax + duplicate key detection | Catches duplicate keys conftest's parser silently merges |
| ruff | Python lint + format | 46K stars, fastest Python linter |
| ty | Python type checking | Astral's type checker, fast |

## Code style

```bash
make fix                         # auto-format + lint
```

Follow existing patterns. Ruff handles formatting automatically.
