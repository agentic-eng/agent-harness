package dockerfile.secrets_test

import rego.v1

import data.dockerfile.secrets

# ── DENY: ENV with secret-like key ──

test_env_api_key_fires if {
	secrets.deny with input as [
		{"Cmd": "env", "Value": ["API_KEY=abc123"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── DENY: ARG with secret-like key ──

test_arg_db_password_fires if {
	secrets.deny with input as [
		{"Cmd": "arg", "Value": ["DB_PASSWORD=hunter2"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── DENY: ENV with token in name ──

test_env_auth_token_fires if {
	secrets.deny with input as [
		{"Cmd": "env", "Value": ["AUTH_TOKEN=xyz"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── PASS: normal ENV without secrets ──

test_normal_env_passes if {
	count(secrets.deny) == 0 with input as [
		{"Cmd": "env", "Value": ["APP_PORT=8080"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "env", "Value": ["NODE_ENV=production"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}
