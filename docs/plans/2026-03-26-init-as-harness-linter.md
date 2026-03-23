# Init as Harness Linter

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `init` the smart harness diagnostic tool — it scans your project, reports what's wrong with your harness config (critical vs. recommendation), and offers to fix it. `lint` stays fast and only runs tool commands + critical checks.

**The insight:** Agent Harness is a linter of linters. `init` diagnoses your harness setup. `lint` runs the harness. Two modes, same Rego policies, different severity thresholds.

**Architecture:** `init` runs conftest in advisory mode (collects both `deny` and `warn`), displays results grouped by preset with severity labels, then offers to scaffold missing files. `lint` runs tool commands (ruff, biome, hadolint) and only fails on `deny` results from Rego policies.

---

## The Two Modes

```
init (diagnostic)                          lint (enforcement)
├── Run ALL Rego policies                  ├── Run tool commands (ruff, biome, etc.)
├── Show deny as "critical"                ├── Run Rego policies
├── Show warn as "recommendation"          ├── Fail on deny only
├── Check tool availability                └── Fast, pass/fail, blocks commits
├── Check missing config files
├── Offer to scaffold/fix
└── Advisory, interactive
```

## Target UX

```
$ agent-harness init

  Scanning python...
    ✗ pyproject.toml: addopts missing --strict-markers         critical
      Fix: add --strict-markers to [tool.pytest.ini_options] addopts
    ✗ pyproject.toml: --cov-fail-under not set                 critical
      Fix: add --cov-fail-under=90 to addopts
    ~ pyproject.toml: ruff output-format is "full"             recommendation
      Consider: set output-format = "concise" for agent-friendly output
    ✓ ruff installed
    ✓ ty installed
    ✓ conftest installed

  Scanning docker...
    ✗ Dockerfile: no HEALTHCHECK instruction                   critical
      Fix: add HEALTHCHECK instruction
    ✗ docker-compose.prod.yml: service 'app' no healthcheck    critical
    ✓ hadolint installed

  Scanning universal...
    ✗ .gitignore: '.env' not ignored                           critical
      Fix: add .env to .gitignore
    ✓ yamllint configured

  Missing files:
    ✗ .agent-harness.yml    → will create
    ✗ Makefile              → will create
    ✗ .yamllint.yml         → will create

  3 critical, 1 recommendation, 3 files to create.

  Apply? [Y/n]
```

After applying, a re-run shows:

```
$ agent-harness init

  Scanning python...
    ✗ pyproject.toml: addopts missing --strict-markers         critical
    ✗ pyproject.toml: --cov-fail-under not set                 critical
    ~ pyproject.toml: ruff output-format is "full"             recommendation
    ✓ ruff installed
    ✓ ty installed

  Scanning docker...
    ✗ Dockerfile: no HEALTHCHECK instruction                   critical

  1 recommendation. 2 critical issues remain (fix manually or run agent-harness fix).
```

## Implementation

### How conftest results map to severity

conftest outputs three categories:
- `FAIL` (from `deny`) → **critical** — must fix for harness to work
- `WARN` (from `warn`) → **recommendation** — nice to have
- `PASS` → not shown (or shown as ✓ in verbose mode)

We already have `deny` and `warn` in all Rego policies. The data is there — we just need to parse conftest output differently in `init` vs `lint`.

### conftest --output for structured parsing

`conftest test --output json` returns structured results we can parse:

```json
[{
  "filename": "pyproject.toml",
  "namespace": "python.pytest",
  "successes": 1,
  "failures": [{"msg": "pytest: addopts missing '--strict-markers'"}],
  "warnings": [{"msg": "pytest: addopts missing '-v'"}]
}]
```

This gives us failures (critical) and warnings (recommendations) separately. Currently `run_check` just looks at exit code. For `init`, we need to parse the JSON output.

---

## File Structure

### New/Modified

```
src/agent_harness/
  conftest.py              # MODIFY: add run_conftest_diagnostic() returning structured results
  preset.py                # MODIFY: add run_diagnostic() to Preset interface
  init/
    scaffold.py            # REWRITE: scan → report → scaffold flow
    diagnostic.py          # CREATE: parse conftest JSON, format diagnostic output

  presets/
    python/__init__.py     # MODIFY: implement run_diagnostic()
    javascript/__init__.py # MODIFY: implement run_diagnostic()
    docker/__init__.py     # MODIFY: implement run_diagnostic()
    dokploy/__init__.py    # MODIFY: implement run_diagnostic()
    universal/__init__.py  # MODIFY: implement run_diagnostic()
```

### Unchanged

- Individual check files (ruff_check.py, biome_check.py, etc.)
- Rego policies
- lint.py, fix.py, detect.py
- runner.py, exclusions.py, workspace.py
- cli.py (minor update to wire new init)

---

## Tasks

### Task 1: Structured conftest output

Add `run_conftest_diagnostic()` to `conftest.py` that runs conftest with `--output json` and returns parsed results with failures (critical) and warnings (recommendations) separated.

**Files:**
- Modify: `src/agent_harness/conftest.py`
- Create: `tests/test_conftest.py`

```python
@dataclass
class DiagnosticResult:
    name: str
    target_file: str
    critical: list[str]      # deny messages
    recommendations: list[str]  # warn messages
    passed: bool


def run_conftest_diagnostic(
    name: str,
    project_dir: Path,
    target_file: str,
    policy_subdir: str,
    data: dict | None = None,
) -> DiagnosticResult:
    """Run conftest with JSON output, parse into critical/recommendation."""
    # ... run conftest test --output json ...
    # ... parse JSON ...
    # ... return DiagnosticResult
```

### Task 2: Add run_diagnostic() to Preset interface

Each preset implements `run_diagnostic()` that returns a list of `DiagnosticResult` — one per config file it checks. Also includes tool availability.

**Files:**
- Modify: `src/agent_harness/preset.py` — add method to base class
- Modify: each preset's `__init__.py` — implement method

```python
# preset.py
class Preset:
    ...
    def run_diagnostic(self, project_dir: Path, config: dict) -> list[DiagnosticResult]:
        """Run all Rego policies in advisory mode. Returns critical + recommendations."""
        return []
```

Example for PythonPreset:
```python
def run_diagnostic(self, project_dir, config):
    results = []
    results.append(run_conftest_diagnostic(
        "python-config", project_dir, "pyproject.toml", "python"
    ))
    return results
```

### Task 3: Diagnostic display module

Create `init/diagnostic.py` that formats DiagnosticResult + tool availability into the target UX.

**Files:**
- Create: `src/agent_harness/init/diagnostic.py`
- Create: `tests/test_diagnostic.py`

```python
def display_diagnostics(
    preset_name: str,
    diagnostics: list[DiagnosticResult],
    tools: list[ToolInfo],
    project_dir: Path,
) -> tuple[int, int]:
    """Display diagnostic results. Returns (critical_count, recommendation_count)."""
    click.echo(f"\n  Scanning {preset_name}...")

    for diag in diagnostics:
        for msg in diag.critical:
            click.echo(f"    ✗ {diag.target_file}: {msg}    critical")
        for msg in diag.recommendations:
            click.echo(f"    ~ {diag.target_file}: {msg}    recommendation")

    for tool in tools:
        available = tool_available(tool.binary, project_dir)
        if available:
            click.echo(f"    ✓ {tool.name} installed")
        else:
            click.echo(f"    ✗ {tool.name} not installed    ({tool.install_hint})")

    # ... return counts
```

### Task 4: Rewrite init/scaffold.py

Wire diagnostic + scaffolding together.

**Files:**
- Modify: `src/agent_harness/init/scaffold.py`
- Modify: `src/agent_harness/cli.py` (minor — init command)
- Modify: `tests/test_init.py`

Flow:
1. Detect stacks
2. For each active preset: run `run_diagnostic()`, display results
3. For universal: run `run_diagnostic()`, display results
4. Check missing config files
5. Show summary (N critical, N recommendations, N files to create)
6. Prompt to scaffold (or `--yes`)
7. Create files

### Task 5: Tests + integration

- Unit tests for diagnostic parsing
- Unit tests for display formatting
- Integration test: run `init` on agent-harness itself, on blog, on a fresh project
- Verify `lint` behavior unchanged (still fast, still pass/fail)

---

## What This Enables

After this, the agent workflow becomes:

1. Agent enters new project
2. Runs `agent-harness init` — sees full diagnostic of harness health
3. Fixes critical issues (or init scaffolds what it can)
4. From now on: `make lint` (fast enforcement)
5. Periodically: `agent-harness init` again to check for drift

The value prop is clear: **agent-harness init tells you everything that's wrong with your development setup, and helps you fix it.**
