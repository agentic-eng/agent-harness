package dockerfile.healthcheck_test

import rego.v1

import data.dockerfile.healthcheck

# ── DENY: no HEALTHCHECK instruction ──

test_missing_healthcheck_fires if {
	healthcheck.deny with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "run", "Value": ["uv sync"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── PASS: HEALTHCHECK present ──

test_with_healthcheck_passes if {
	count(healthcheck.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "healthcheck", "Value": ["CMD curl -f http://localhost/ || exit 1"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}
