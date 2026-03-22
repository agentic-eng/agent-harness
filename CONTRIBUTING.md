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

1. **Choose the right directory:**
   - `policies/dockerfile/` — Dockerfile rules
   - `policies/compose/` — Docker Compose rules
   - `policies/python/` — pyproject.toml / Python config rules
   - `policies/gitignore/` — .gitignore rules

2. **Write the .rego file.** Package name must match the directory structure:
   ```rego
   package dockerfile.my_concern

   import rego.v1

   deny contains msg if {
       # your logic here
       msg := "clear error message telling the agent exactly what to fix"
   }
   ```

3. **Write test fixtures.** Place them in `tests/test_checks/` — create files prefixed `bad_` (should fail) and `good_` (should pass).

4. **Run conftest directly to verify:**
   ```bash
   # Dockerfile example
   conftest test tests/test_checks/bad_example.Dockerfile \
     --parser dockerfile \
     -p policies/dockerfile/ \
     --all-namespaces

   # Python/TOML example
   conftest test tests/test_checks/bad_pyproject.toml \
     --parser toml \
     -p policies/python/ \
     --all-namespaces
   ```

5. **Wire into the check module** if your policy targets a new file type. Existing file types (Dockerfile, docker-compose.prod.yml, pyproject.toml, .gitignore) are already wired.

6. **Update README.md** rule count if you added new deny rules.

## Adding a new check module

Create a new file in `src/ai_harness/checks/`. Follow the existing pattern:

- Function takes `project_dir: Path` and returns `CheckResult`
- Use `run_check()` from `ai_harness.runner` for subprocess execution
- Add the call to `run_lint()` in `src/ai_harness/lint.py`

Look at `src/ai_harness/checks/hadolint.py` or `src/ai_harness/checks/ruff.py` for reference.

## Evaluating community rule ideas

Before writing a new Rego policy, check if an existing tool already covers it:

- **hadolint** covers most Dockerfile best practices (DL/SC rules)
- **ruff** covers Python linting, imports, formatting
- **yamllint** covers YAML syntax and style

If an existing tool already enforces the rule, don't duplicate it in Rego. Write Rego policies for things no existing tool covers — structural requirements, cross-field validation, project-level configuration checks.

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
