package dockerfile.user

# USER INSTRUCTION — no running as root
#
# WHAT: Ensures at least one USER instruction exists so the container
# does not run as root.
#
# WHY: Agents generate Dockerfiles that run as root by default. A container
# escape vulnerability gives the attacker root on the host. CIS Docker
# Benchmark 4.1 requires non-root users.
#
# WITHOUT IT: Containers run as root — one exploit away from full host
# compromise. Every security scanner will flag it.
#
# FIX: Add `USER nonroot` (or another non-root user) near the end of
# the Dockerfile, after installing dependencies.
#
# Input: flat array of Dockerfile instructions [{Cmd, Flags, Value, Stage}, ...]

import rego.v1

default _exceptions := []

_exceptions := data.exceptions if {
	data.exceptions
}

# ── Policy: must have USER instruction ──

deny contains msg if {
	not "dockerfile.user" in _exceptions
	not _has_user_instruction
	msg := "Dockerfile has no USER instruction — containers should not run as root. Add 'USER nonroot' or similar."
}

_has_user_instruction if {
	some instr in input
	instr.Cmd == "user"
}
