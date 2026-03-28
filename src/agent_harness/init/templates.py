HARNESS_YML = """\
# AI Harness configuration
# Detected stacks: {stacks}
stacks: [{stacks_list}]

# exclude:
#   - _archive/
#   - vendor/

# python:
#   coverage_threshold: 95
#   line_length: 120

# javascript:
#   coverage_threshold: 80

# docker:
#   own_image_prefix: "ghcr.io/myorg/"

# security:
#   base_branch: origin/main
#   ignore:
#     - id: CVE-2025-XXXX
#       reason: "No fix available, transitive dep"
#       expires: 2026-06-01
"""

YAMLLINT_YML = """\
extends: default
ignore: |
  .venv/
  node_modules/
rules:
  line-length:
    max: 200
  truthy:
    check-keys: false
  document-start: disable
  indentation: disable
"""

PRECOMMIT_YML = """\
repos:
  - repo: local
    hooks:
      - id: harness-fix
        name: auto-fix
        entry: agent-harness fix
        language: system
        pass_filenames: false
        always_run: true

      - id: harness-lint
        name: agent-harness lint
        entry: agent-harness lint
        language: system
        pass_filenames: false
        always_run: true
"""

MAKEFILE = """\
.PHONY: lint fix test check security-audit bootstrap

lint:
\tagent-harness lint

fix:
\tagent-harness fix

test:
\t{test_command}

security-audit:
\tagent-harness security-audit

check: lint test security-audit

bootstrap: ## First-time setup after clone
\t{install_deps}
\tagent-harness init --apply
\t@if command -v prek >/dev/null; then prek install; \\
\telif command -v pre-commit >/dev/null; then pre-commit install; \\
\telse echo "Install prek (brew install prek) or pre-commit for git hooks"; fi
\t@echo "Done. Run 'make check' to verify."
"""

MAKEFILE_PYTHON = """\
.PHONY: lint fix test check coverage-diff security-audit bootstrap

lint:
\tagent-harness lint

fix:
\tagent-harness fix

test:
\t{test_command}

coverage-diff:
\t@uv run diff-cover coverage.xml --compare-branch=origin/main --fail-under=95

security-audit:
\tagent-harness security-audit

check: lint test coverage-diff security-audit

bootstrap: ## First-time setup after clone
\tuv sync
\tagent-harness init --apply
\t@if command -v prek >/dev/null; then prek install; \\
\telif command -v pre-commit >/dev/null; then pre-commit install; \\
\telse echo "Install prek (brew install prek) or pre-commit for git hooks"; fi
\t@echo "Done. Run 'make check' to verify."
"""

CLAUDEMD = """\
# {project_name}

## Dev Commands

```bash
make lint          # agent-harness lint (runs all checks, safe anytime)
make fix           # auto-fix formatting, then lint
make test          # run tests{coverage_note}
make security-audit          # check deps + secrets in working dir (fast)
make check                   # full gate: lint + test{coverage_diff_note} + security-audit
make bootstrap               # first-time setup: deps + harness config + pre-commit hooks
agent-harness security-audit-history  # deep scan git history for deleted secrets (run once)
```

## Workflow

Pre-commit hooks run `agent-harness fix` and `agent-harness lint` automatically on every commit.
Before declaring work done, always run `make check` — it's the full quality gate.{coverage_diff_workflow}
On first setup or when onboarding a new repo, run `agent-harness security-audit-history` once to scan full git history for leaked secrets.

## Never

- Never truncate lint/test output with `| tail` or `| head` — output is already optimized
- Never skip `make check` before declaring a task complete
"""
