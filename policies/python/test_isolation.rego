package python.test_isolation

# pyproject.toml policy: test environment isolation.
# Ensures pytest-env is configured so agents can't accidentally hit production.
#
# Input: parsed pyproject.toml (TOML → JSON)

import rego.v1

# ── Policy: pytest-env configured ──
# Without this, agents run tests against whatever DATABASE_URL is in the shell.
# pytest-env injects test values BEFORE pydantic-settings reads them.

deny contains msg if {
	opts := input.tool.pytest.ini_options
	not opts.env
	msg := "pytest: no 'env' configuration — add pytest-env entries to isolate tests from production (e.g., test database URL on a separate port)"
}
