package python.ruff_test

import rego.v1

import data.python.ruff

# ── DENY: missing output-format ──

test_missing_output_format_fires if {
	ruff.deny with input as {"tool": {"ruff": {"line-length": 140, "lint": {"mccabe": {"max-complexity": 10}}}}}
}

# ── DENY: wrong output-format ──

test_wrong_output_format_fires if {
	ruff.deny with input as {"tool": {"ruff": {"output-format": "full", "line-length": 140, "lint": {"mccabe": {"max-complexity": 10}}}}}
}

# ── DENY: missing line-length ──

test_missing_line_length_fires if {
	ruff.deny with input as {"tool": {"ruff": {"output-format": "concise", "lint": {"mccabe": {"max-complexity": 10}}}}}
}

# ── DENY: short line-length ──

test_short_line_length_fires if {
	ruff.deny with input as {"tool": {"ruff": {"output-format": "concise", "line-length": 80, "lint": {"mccabe": {"max-complexity": 10}}}}}
}

# ── DENY: missing complexity ──

test_missing_complexity_fires if {
	ruff.deny with input as {"tool": {"ruff": {"output-format": "concise", "line-length": 140, "lint": {}}}}
}

# ── DENY: complexity too high ──

test_high_complexity_fires if {
	ruff.deny with input as {"tool": {"ruff": {"output-format": "concise", "line-length": 140, "lint": {"mccabe": {"max-complexity": 20}}}}}
}

# ── PASS: good config ──

test_good_config_passes if {
	count(ruff.deny) == 0 with input as {"tool": {"ruff": {"output-format": "concise", "line-length": 140, "lint": {"mccabe": {"max-complexity": 10}}}}}
}
