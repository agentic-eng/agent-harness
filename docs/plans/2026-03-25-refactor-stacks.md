# Refactor: Stack Separation + Rename

> **For agentic workers:** Use superpowers:subagent-driven-development to implement.

**Goal:** Rename ai_harness → agent_harness, restructure checks into per-stack directories with one check per file, one test per check.

**Why:** Adding Ruby/Go/JS later should be "create a new stacks/ directory" not "edit 5 existing files." Each check is a self-contained unit with its own test.

## Current structure (flat)
```
src/ai_harness/checks/conftest.py     # 5 functions mixed
src/ai_harness/checks/ruff.py
src/ai_harness/checks/ty.py
src/ai_harness/checks/hadolint.py
src/ai_harness/checks/yamllint_check.py
src/ai_harness/checks/file_length.py
```

## Target structure (per-stack, one file per check)
```
src/agent_harness/
  cli.py, config.py, runner.py, lint.py, fix.py, audit.py
  stacks/
    python/
      detect.py, ruff_check.py, ty_check.py, file_length_check.py, 
      conftest_python.py, templates.py
    docker/
      detect.py, hadolint_check.py, conftest_dockerfile.py,
      conftest_compose.py, templates.py
    universal/
      yamllint_check.py, conftest_json.py, conftest_gitignore.py,
      templates.py

tests/
  stacks/python/test_ruff_check.py, test_ty_check.py, ...
  stacks/docker/test_hadolint_check.py, ...
  stacks/universal/test_yamllint_check.py, ...
  fixtures/dockerfile/, fixtures/compose/
  test_cli.py, test_config.py, test_detect.py, test_runner.py
```

## Convention: every check file is self-documented

Same pattern as Rego policies. Every check file has a module docstring:

```python
"""
<Check name>.

WHAT: <One sentence — what this check does>

WHY: <2-3 sentences — why AI agents need this specific check>

WITHOUT IT: <Concrete failure scenario>

FIX: <How to resolve — exact command or action>

REQUIRES: <External tool(s) needed>
"""
```

The file IS the documentation. An agent reading the file understands everything — no external docs needed. When a user challenges a check, the agent reads the docstring and cites the WHY.

## Three test layers

| Layer | What it tests | How to run | Files |
|---|---|---|---|
| **Rego unit tests** | Policy logic with mock input | `conftest verify -p policies/` | `policies/**/*_test.rego` |
| **Fixture integration tests** | Policies against real Dockerfiles/compose | `conftest test tests/fixtures/...` | `tests/fixtures/**` |
| **Python unit tests** | Check modules (subprocess, fallback, skip) | `uv run pytest tests/` | `tests/stacks/**` |

Every Rego policy gets a `_test.rego` sibling:

```
policies/
  dockerfile/
    layers.rego              # The policy
    layers_test.rego          # Rego unit test — mock input, assert deny/no-deny
    cache.rego
    cache_test.rego
    ...
  compose/
    images.rego
    images_test.rego
    ...
```

Rego unit test example:
```rego
package dockerfile.layers_test

import data.dockerfile.layers

test_broad_copy_before_deps {
    layers.deny with input as [
        {"Cmd": "from", "Value": ["python:3.12"], "Flags": [], "Stage": 0, "SubCmd": ""},
        {"Cmd": "copy", "Value": [".", "."], "Flags": [], "Stage": 0, "SubCmd": ""},
        {"Cmd": "run", "Value": ["uv sync"], "Flags": [], "Stage": 0, "SubCmd": ""},
    ]
}

test_correct_order_passes {
    count(layers.deny) == 0 with input as [
        {"Cmd": "from", "Value": ["python:3.12"], "Flags": [], "Stage": 0, "SubCmd": ""},
        {"Cmd": "copy", "Value": ["pyproject.toml", "./"], "Flags": [], "Stage": 0, "SubCmd": ""},
        {"Cmd": "run", "Value": ["uv sync"], "Flags": ["--mount=type=cache,target=/root/.cache/uv"], "Stage": 0, "SubCmd": ""},
        {"Cmd": "copy", "Value": ["src/", "./src/"], "Flags": [], "Stage": 0, "SubCmd": ""},
    ]
}
```

Fixture integration tests stay in `tests/fixtures/` — real files that conftest runs against. These test the full pipeline (parser + policy), while Rego unit tests test policy logic in isolation.

## Tasks
1. Rename ai_harness → agent_harness (module name, imports, pyproject.toml)
2. Create stacks/ directory structure
3. Move checks into per-stack directories (one file per check, with WHAT/WHY/WITHOUT IT/FIX docstrings)
4. Write Rego unit tests (`*_test.rego`) for all 15 policy files
5. Move Python tests to mirror stacks/ structure (one test file per check file)
6. Update lint.py to discover checks from stacks/
7. Update all imports
8. Move config templates from K skill's python.md/docker.md into per-stack templates.py
9. Verify all three test layers pass:
   - `conftest verify -p policies/`
   - `conftest test tests/fixtures/dockerfile/*.Dockerfile --parser dockerfile -p policies/dockerfile/ --all-namespaces`
   - `uv run pytest tests/ -v`
10. Test on aggre
11. Strip K skill's python.md and docker.md to guidance-only (non-deterministic advice)
