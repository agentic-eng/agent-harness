package gitignore.secrets_test

import data.gitignore.secrets
import rego.v1

# Helper: minimal .gitignore with all required entries
mock_complete_input := [
	{"Kind": "Path", "Value": ".env", "Original": ".env"},
	{"Kind": "Path", "Value": ".venv/", "Original": ".venv/"},
	{"Kind": "Path", "Value": "__pycache__/", "Original": "__pycache__/"},
	{"Kind": "Path", "Value": "node_modules/", "Original": "node_modules/"},
	{"Kind": "Path", "Value": "dist/", "Original": "dist/"},
]

# Universal: .env always required
test_missing_env if {
	count(secrets.deny) > 0 with input as []
		with data.stacks as []
}

test_env_present if {
	count(secrets.deny) == 0 with input as mock_complete_input
		with data.stacks as ["python", "javascript"]
}

# Python: .venv required only when python detected
test_venv_required_for_python if {
	count(secrets.deny) > 0 with input as [{"Kind": "Path", "Value": ".env", "Original": ".env"}]
		with data.stacks as ["python"]
}

test_venv_not_required_without_python if {
	denials := secrets.deny with input as [{"Kind": "Path", "Value": ".env", "Original": ".env"}]
		with data.stacks as ["javascript"]
	not _contains_venv(denials)
}

_contains_venv(denials) if {
	some msg in denials
	contains(msg, ".venv")
}

# JavaScript: node_modules required only when javascript detected
test_node_modules_required_for_js if {
	count(secrets.deny) > 0 with input as [{"Kind": "Path", "Value": ".env", "Original": ".env"}]
		with data.stacks as ["javascript"]
}

test_node_modules_not_required_without_js if {
	denials := secrets.deny with input as [
		{"Kind": "Path", "Value": ".env", "Original": ".env"},
		{"Kind": "Path", "Value": ".venv/", "Original": ".venv/"},
		{"Kind": "Path", "Value": "__pycache__/", "Original": "__pycache__/"},
	]
		with data.stacks as ["python"]
	not _contains_node_modules(denials)
}

_contains_node_modules(denials) if {
	some msg in denials
	contains(msg, "node_modules")
}
