package python.test_isolation_test

import rego.v1

import data.python.test_isolation

# ── DENY: missing env config ──

test_missing_env_fires if {
	test_isolation.deny with input as {"tool": {"pytest": {"ini_options": {"addopts": "-v"}}}}
}

# ── PASS: env configured ──

test_with_env_passes if {
	count(test_isolation.deny) == 0 with input as {"tool": {"pytest": {"ini_options": {
		"addopts": "-v",
		"env": ["DATABASE_URL=postgresql://localhost:5433/test_db"],
	}}}}
}
