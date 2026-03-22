"""Python stack config templates — reference configs for agent-harness init.

These templates are extracted from the ai-harness K skill (python.md).
They are NOT used by `init` yet — stored here for a future enhancement
that will generate pyproject.toml sections, CI workflows, and Dockerfiles.
"""

# Full [tool.ruff] TOML section for pyproject.toml.
# Configures linter + formatter with 4-tier rule organization:
#   PREVENT (hard errors), ENFORCE (deterministic style),
#   DETECT (flags for evaluation), STRUCTURE (architecture).
# Use when initializing ruff config in a new Python project.
RUFF_CONFIG = """\
[tool.ruff]
target-version = "py312"
line-length = 140           # Reduces unnecessary wrapping = less diff noise
output-format = "concise"   # One-line errors, no context blocks

[tool.ruff.lint]
select = [
    # ── PREVENT: Agent cannot commit these — hard errors, no ambiguity ──
    "F",         # pyflakes — undefined names, unused imports (code won't run)
    "S",         # flake8-bandit — security: hardcoded passwords, SQL injection, exec()
    "T10",       # flake8-debugger — leftover pdb/breakpoint() statements
    "T20",       # flake8-print — leftover print() debug statements
    "BLE",       # flake8-blind-except — bare except: hides all errors
    "PGH",       # pygrep-hooks — blanket type: ignore, eval(), blanket noqa

    # ── ENFORCE: Deterministic style — no debates, auto-fixable ──
    "E", "W",    # pycodestyle — basic style errors and warnings
    "I",         # isort — import sorting
    "N",         # pep8-naming — naming conventions (functions snake_case, classes PascalCase)
    "UP",        # pyupgrade — upgrade to modern Python syntax
    "C4",        # flake8-comprehensions — unnecessary list()/dict()/set() wrappers
    "PIE",       # flake8-pie — unnecessary code patterns (pass in class body, etc.)
    "TC",        # flake8-type-checking — move type-only imports behind TYPE_CHECKING
    "PTH",       # flake8-use-pathlib — os.path → pathlib (modern, cross-platform)
    "FURB",      # refurb — modernization (check(x), isinstance patterns, etc.)
    "RUF",       # ruff-specific — additional quality rules

    # ── DETECT: Flags potential problems for agent to evaluate ──
    "B",         # flake8-bugbear — likely bugs (mutable defaults, assert False, etc.)
    "A",         # flake8-builtins — shadowing builtins (list, type, id, input)
    "DTZ",       # flake8-datetimez — naive datetime (timezone bugs)
    "ISC",       # flake8-implicit-str-concat — accidental string concatenation
    "RET",       # flake8-return — unnecessary return/else/elif after return
    "SIM",       # flake8-simplify — simplifiable code patterns
    "ARG",       # flake8-unused-arguments — unused function arguments
    "PERF",      # perflint — performance anti-patterns (unnecessary list copies, etc.)
    "LOG",       # flake8-logging — logging anti-patterns
    "G",         # flake8-logging-format — f-strings in log messages (use structured fields)
    "SLF",       # flake8-self — private member access from outside class
    "TID",       # flake8-tidy-imports — banned imports, relative imports
    "PL",        # pylint subset — complexity, design, conventions

    # ── STRUCTURE: Clean architecture enforcement ──
    "C90",       # mccabe — cyclomatic complexity limit
    "EM",        # flake8-errmsg — string literals in exceptions (error messages as variables)
    "FBT",       # flake8-boolean-trap — boolean positional arguments (use keyword args)
    "PT",        # flake8-pytest-style — pytest best practices
]
ignore = [
    # Readability — agent rewrites hurt more than they help
    "SIM108",    # ternary — often hurts readability in multi-line expressions
    "SIM110",    # any() rewrite — comprehension often clearer than loop
    "RUF001",    # ambiguous unicode — intentional Cyrillic/emoji usage
    "RUF015",    # next(iter()) vs [0] — readability preference

    # Too strict — valid patterns flagged
    "EM101",     # string literal in exception — too strict for simple ValueError("msg")
    "EM102",     # f-string in exception — same
    "FBT001",    # boolean positional arg def — too noisy for simple enable/disable flags
    "FBT002",    # boolean default value — same
    "PLR0913",   # too many arguments — sometimes unavoidable (config constructors)
    "PLR2004",   # magic value comparison — too noisy (thresholds, HTTP status codes)
    "ARG001",    # unused function argument — fixtures, callbacks, interface conformance
    # Agent-hostile — causes harmful refactoring
    "A003",      # class attribute shadows builtin — Pydantic models use `id`, `type`, `input`
    "PT001",     # @pytest.fixture() vs @pytest.fixture — pure style, zero bug prevention
    "PT023",     # @pytest.mark.unit() vs @pytest.mark.unit — same
    "PERF203",   # try/except in loop — conflicts with fail-soft per-item processing
    "RET504",    # unnecessary assignment before return — useful for debugging
    "PLW2901",   # loop variable overwritten — `for line in lines: line = line.strip()` is fine
]
extend-exclude = ["alembic/versions"]   # Skip generated code

[tool.ruff.lint.mccabe]
max-complexity = 10    # Functions above 10 branches must be split

[tool.ruff.lint.pylint]
max-args = 8           # More than 8 → pass a config object or dataclass
max-statements = 50    # More than 50 → extract functions
max-branches = 10      # Mirrors mccabe
max-returns = 6        # Too many returns → confusing control flow

[tool.ruff.lint.per-file-ignores]
"tests/**" = [
    "S101",      # assert — standard in tests
    "S106",      # hardcoded passwords — test fixtures use fake creds
    "E402",      # import order — tests set env vars before imports
    "ARG001",    # unused arguments — pytest fixtures
    "PLR2004",   # magic values — test assertions use literal values
    "SLF001",    # private member access — testing internals is valid
    "PT011",     # pytest.raises too broad — sometimes intentional
    "PLR0915",   # too many statements — long test scenarios are valid
]
"""

# [tool.ty] TOML section for pyproject.toml.
# Configures the ty type checker with error-level rules for AI agents.
# Use when initializing type checking in a new Python project.
TY_CONFIG = """\
[tool.ty.environment]
python-version = "3.12"
python = "./.venv"          # Resolves third-party package types from venv

[tool.ty.src]
root = ["src"]              # Where source code lives
include = ["tests"]         # Type-check tests too — catches mock/fixture type bugs

[tool.ty.rules]
possibly-unresolved-reference = "error"
invalid-argument-type = "error"
missing-argument = "error"
unsupported-operator = "error"
division-by-zero = "error"
unused-ignore-comment = "warn"
redundant-cast = "warn"
"""

# [tool.pytest.ini_options] TOML section for pyproject.toml.
# Configures pytest with strict markers, verbose output, and coverage gates.
# Use when initializing test configuration in a new Python project.
PYTEST_CONFIG = """\
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --strict-markers --cov --cov-report=term:skip-covered --cov-report=xml --cov-fail-under=95"
markers = [
    "unit: unit tests",
    "integration: integration tests",
    "contract: external API verification",
]
"""

# [tool.coverage.run] and [tool.coverage.report] TOML sections for pyproject.toml.
# Configures coverage with branch tracking, noise reduction, and structural exclusions.
# Use when initializing coverage in a new Python project.
# Note: {package} should be replaced with the actual package name.
COVERAGE_CONFIG = """\
[tool.coverage.run]
source = ["src/{package}"]
branch = true
omit = ["src/{package}/cli.py"]  # Composition roots — integration-tested via the system

[tool.coverage.report]
show_missing = false      # Don't list line numbers (agent sees them in the code)
skip_covered = true       # Only show files with gaps — critical for noise reduction
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.",
    "if TYPE_CHECKING:",
    "class .*\\\\bProtocol\\\\):",
    "\\\\.\\\\.\\\\.",            # Protocol method bodies
]
"""

# GitHub Actions CI workflow for Python + uv projects.
# Uses astral-sh/setup-uv with caching, frozen lockfile, and Makefile targets.
# Use when initializing CI in a new Python project.
CI_WORKFLOW = """\
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true    # Caches .venv across runs

      - name: Install dependencies
        run: uv sync --frozen

      - name: Lint
        run: make lint

      - name: Test
        run: make test

      - name: Diff coverage
        if: github.event_name == 'pull_request'
        run: make coverage-diff
"""

# Python + uv Dockerfile template.
# Uses multi-layer caching: system deps, Python deps, then source.
# Use when initializing a Dockerfile for a Python + uv project.
# Note: <system-deps> should be replaced with actual system dependencies.
DOCKERFILE_TEMPLATE = """\
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app

# System deps (rarely change — cached layer)
RUN apt-get update && apt-get install -y --no-install-recommends \\
    <system-deps> \\
    && rm -rf /var/lib/apt/lists/*

# Python deps (change occasionally — cached separately from source)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Source (changes often — only this layer rebuilds on code change)
COPY src/ ./src/
RUN uv sync --frozen --no-dev

ENV UV_NO_SYNC=true    # Skip uv overhead at runtime
"""
