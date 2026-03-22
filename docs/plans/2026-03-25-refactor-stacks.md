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

## Tasks
1. Rename ai_harness → agent_harness (module name, imports, pyproject.toml)
2. Create stacks/ directory structure
3. Move checks into per-stack directories (one file per check)
4. Move tests to mirror structure
5. Update lint.py to discover checks from stacks/
6. Update all imports
7. Move config templates into per-stack templates.py
8. Verify all tests pass
9. Test on aggre
