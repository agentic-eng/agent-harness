HARNESS_YML = """\
# AI Harness configuration
# Detected stacks: {stacks}
stacks: [{stacks_list}]

# exclude:
#   - _archive/
#   - vendor/

# python:
#   coverage_threshold: 95
#   line_length: 140

# javascript:
#   coverage_threshold: 80

# docker:
#   own_image_prefix: "ghcr.io/myorg/"
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
      - id: harness-lint
        name: agent-harness lint
        entry: agent-harness lint
        language: system
        pass_filenames: false
        always_run: true
"""

MAKEFILE = """\
.PHONY: lint fix test

lint:
\tagent-harness lint

fix:
\tagent-harness fix

test:
\t{test_command}
"""
