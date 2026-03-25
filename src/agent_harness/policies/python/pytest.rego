package python.pytest

# PYTEST CONFIG — strict markers, integrated coverage
#
# WHAT: Ensures pytest is configured with strict markers and coverage.
# These are gates that must exist. Value judgments (thresholds, verbosity)
# are handled by init setup checks, not lint.
#
# LINT RULES (deny): Gate exists? Is it objectively broken?
# INIT CHECKS (Python): Is it optimally configured? Fix it.
#
# Input: parsed pyproject.toml (TOML -> JSON)

import rego.v1

# ── deny: strict-markers must be enabled ──

deny contains msg if {
	opts := input.tool.pytest.ini_options
	addopts := opts.addopts
	not contains(addopts, "--strict-markers")
	msg := "pytest: addopts missing '--strict-markers' — catches marker typos deterministically"
}

# ── deny: coverage must be enabled ──

deny contains msg if {
	opts := input.tool.pytest.ini_options
	addopts := opts.addopts
	not contains(addopts, "--cov")
	msg := "pytest: addopts missing '--cov' — coverage should run with every test invocation"
}

# ── deny: coverage threshold must exist ──

deny contains msg if {
	opts := input.tool.pytest.ini_options
	addopts := opts.addopts
	not contains(addopts, "--cov-fail-under")
	msg := "pytest: addopts missing '--cov-fail-under' — set a coverage threshold (recommended: 95)"
}

# ── deny: coverage threshold must not be absurdly low ──
# Below 30% is not a gate — it catches nothing meaningful.

deny contains msg if {
	opts := input.tool.pytest.ini_options
	addopts := opts.addopts
	contains(addopts, "--cov-fail-under")
	parts := split(addopts, "--cov-fail-under=")
	count(parts) > 1
	threshold_str := split(parts[1], " ")[0]
	threshold := to_number(threshold_str)
	threshold < 30
	msg := sprintf("pytest: --cov-fail-under=%v is below 30%% — this gate catches nothing meaningful", [threshold])
}
