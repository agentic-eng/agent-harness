package dockerfile.user_test

import rego.v1

import data.dockerfile.user

# ── DENY: no USER instruction ──

test_missing_user_fires if {
	user.deny with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "run", "Value": ["uv sync"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── PASS: USER instruction present ──

test_with_user_passes if {
	count(user.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "user", "Value": ["nonroot"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}
