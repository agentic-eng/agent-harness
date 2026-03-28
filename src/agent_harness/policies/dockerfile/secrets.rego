package dockerfile.secrets

# SECRETS — no credentials in ENV/ARG
#
# WHAT: Detects sensitive values (passwords, API keys, tokens) passed via
# ENV or ARG instructions in Dockerfiles.
#
# WHY: Agents hardcode API keys and passwords in ENV/ARG. Build args are
# visible in image history via `docker history`. ENV values persist in
# the final image. Anyone with image access can extract them.
#
# WITHOUT IT: Secrets leaked in image layers, extractable by anyone with
# image access. Credentials end up in registries and CI logs.
#
# FIX: Use runtime environment variables or mounted secrets instead.
# Never bake secrets into the image at build time.
#
# Input: flat array of Dockerfile instructions [{Cmd, Flags, Value, Stage}, ...]

import rego.v1

default _exceptions := []

_exceptions := data.exceptions if {
	data.exceptions
}

# Suspicious key patterns (case-insensitive matching via regex)
secret_patterns := [
	"password",
	"passwd",
	"secret",
	"api_key",
	"apikey",
	"api.key",
	"access_key",
	"access_token",
	"auth_token",
	"private_key",
	"token",
	"credential",
]

# ── Policy: no secrets in ENV ──

deny contains msg if {
	not "dockerfile.secrets" in _exceptions
	some instr in input
	instr.Cmd == "env"
	some val in instr.Value

	# ENV can be "KEY=value" or just "KEY value"
	key := _extract_env_key(val)
	_is_secret_key(key)

	msg := sprintf("ENV '%s' looks like a secret — never bake secrets into images. Use runtime env vars or mounted secrets.", [key])
}

# ── Policy: no secrets in ARG ──

deny contains msg if {
	not "dockerfile.secrets" in _exceptions
	some instr in input
	instr.Cmd == "arg"
	some val in instr.Value

	key := _extract_arg_key(val)
	_is_secret_key(key)

	msg := sprintf("ARG '%s' looks like a secret — build args are visible in image history. Use runtime env vars or mounted secrets.", [key])
}

# ── Helpers ──

_extract_env_key(val) := key if {
	contains(val, "=")
	key := split(val, "=")[0]
} else := val

_extract_arg_key(val) := key if {
	contains(val, "=")
	key := split(val, "=")[0]
} else := val

_is_secret_key(key) if {
	some pattern in secret_patterns
	regex.match(sprintf("(?i)%s", [pattern]), key)
}
