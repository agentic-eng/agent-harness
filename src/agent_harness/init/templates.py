HARNESS_YML = """\
# AI Harness configuration
# Detected stacks: {stacks}
stacks: [{stacks_list}]

# python:
#   coverage_threshold: 95
#   line_length: 140
#   max_file_lines: 500

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
        name: ai-harness lint
        entry: ai-harness lint
        language: system
        pass_filenames: false
        always_run: true
"""
