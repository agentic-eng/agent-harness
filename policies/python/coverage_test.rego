package python.coverage_test

import rego.v1

import data.python.coverage

# ── DENY: missing skip_covered ──

test_missing_skip_covered_fires if {
	coverage.deny with input as {"tool": {"coverage": {
		"report": {},
		"run": {"branch": true},
	}}}
}

# ── DENY: skip_covered = false ──

test_skip_covered_false_fires if {
	coverage.deny with input as {"tool": {"coverage": {
		"report": {"skip_covered": false},
		"run": {"branch": true},
	}}}
}

# ── DENY: missing branch ──

test_missing_branch_fires if {
	coverage.deny with input as {"tool": {"coverage": {
		"report": {"skip_covered": true},
		"run": {},
	}}}
}

# ── DENY: branch = false ──

test_branch_false_fires if {
	coverage.deny with input as {"tool": {"coverage": {
		"report": {"skip_covered": true},
		"run": {"branch": false},
	}}}
}

# ── PASS: good config ──

test_good_config_passes if {
	count(coverage.deny) == 0 with input as {"tool": {"coverage": {
		"report": {"skip_covered": true},
		"run": {"branch": true},
	}}}
}
