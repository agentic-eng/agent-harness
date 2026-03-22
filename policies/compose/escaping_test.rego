package compose.escaping_test

import rego.v1

import data.compose.escaping

# ── DENY: bare $ in environment (object format) ──

test_bare_dollar_in_env_object_fires if {
	escaping.deny with input as {"services": {"app": {
		"environment": {"HASH": "$2a$12$abcdef"},
	}}}
}

# ── DENY: bare $ in environment (list format) ──

test_bare_dollar_in_env_list_fires if {
	escaping.deny with input as {"services": {"app": {
		"environment": ["HASH=$2a$12$abcdef"],
	}}}
}

# ── PASS: escaped $$ in environment ──

test_escaped_dollar_passes if {
	count(escaping.deny) == 0 with input as {"services": {"app": {
		"environment": {"HASH": "$$2a$$12$$abcdef"},
	}}}
}

# ── PASS: no dollar signs at all ──

test_no_dollar_passes if {
	count(escaping.deny) == 0 with input as {"services": {"app": {
		"environment": {"PORT": "8080"},
	}}}
}
