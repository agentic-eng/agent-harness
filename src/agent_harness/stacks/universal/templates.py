"""Universal stack config templates — reference configs for agent-harness init.

These templates are extracted from the ai-harness K skill (SKILL.md).
They are NOT used by `init` yet — stored here for a future enhancement
that will generate yamllint and pre-commit configs.
"""

# yamllint configuration for .yamllint.yml.
# Tuned to avoid false positives that waste agent cycles:
# long URLs, GitHub Actions `on:` triggers, document-start markers.
# Use when initializing YAML linting in any project.
YAMLLINT_CONFIG = """\
extends: default

ignore: |
  .venv/
  node_modules/

rules:
  line-length:
    max: 200              # YAML configs have long URLs; default 80 causes constant false positives
  truthy:
    check-keys: false     # Without this, `on:` in GitHub Actions is flagged as truthy value
  document-start: disable # `---` at top of every YAML is noise
  indentation: disable    # Let the formatter handle it
"""

# Pre-commit config for .pre-commit-config.yaml.
# Uses local-only hooks that delegate to Makefile — single source of truth.
# Fix runs before lint: auto-correct first, then verify.
# Use when initializing pre-commit hooks in any project.
PRECOMMIT_CONFIG = """\
repos:
  - repo: local
    hooks:
      - id: fix
        name: auto-fix
        entry: make fix
        language: system
        pass_filenames: false
        always_run: true

      - id: lint
        name: lint
        entry: make lint
        language: system
        pass_filenames: false
        always_run: true
"""
