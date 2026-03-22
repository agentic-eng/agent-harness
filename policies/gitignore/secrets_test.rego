package gitignore.secrets_test

import rego.v1

import data.gitignore.secrets

# ── DENY: missing .env ──

test_missing_env_fires if {
	secrets.deny with input as [
		{"Kind": "Path", "Value": ".venv", "Original": ".venv"},
		{"Kind": "Path", "Value": "__pycache__", "Original": "__pycache__"},
	]
}

# ── DENY: empty gitignore ──

test_empty_gitignore_fires if {
	secrets.deny with input as []
}

# ── PASS: all required patterns present ──

test_complete_gitignore_passes if {
	count(secrets.deny) == 0 with input as [
		{"Kind": "Path", "Value": ".env", "Original": ".env"},
		{"Kind": "Path", "Value": ".venv", "Original": ".venv"},
		{"Kind": "Path", "Value": "__pycache__", "Original": "__pycache__"},
	]
}
