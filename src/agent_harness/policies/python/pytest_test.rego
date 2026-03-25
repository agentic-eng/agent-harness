package python.pytest_test

import rego.v1

import data.python.pytest

# ── DENY: missing strict-markers ──

test_missing_strict_markers_fires if {
	pytest.deny with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v --cov --cov-fail-under=95"}}}}
}

# ── DENY: missing --cov ──

test_missing_cov_fires if {
	pytest.deny with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v --strict-markers --cov-fail-under=95"}}}}
}

# ── DENY: missing --cov-fail-under ──

test_missing_cov_fail_under_fires if {
	pytest.deny with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v --strict-markers --cov"}}}}
}

# ── DENY: absurdly low threshold ──

test_threshold_below_30_fires if {
	pytest.deny with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v --strict-markers --cov --cov-fail-under=15"}}}}
}

# ── PASS: threshold at 30 is acceptable ──

test_threshold_at_30_passes if {
	count(pytest.deny) == 0 with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v --strict-markers --cov --cov-fail-under=30"}}}}
}

# ── PASS: good config ──

test_good_config_passes if {
	count(pytest.deny) == 0 with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v --strict-markers --cov --cov-fail-under=95"}}}}
}
