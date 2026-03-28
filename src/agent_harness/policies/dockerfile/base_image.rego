package dockerfile.base_image

# BASE IMAGE — no Alpine for musl-sensitive stacks
#
# WHAT: Warns when Alpine base is used with Python, Node, or Ruby stacks
# that have musl libc compatibility issues.
#
# WHY: Agents pick Alpine because it's small, but musl libc breaks native
# extensions in Python/Node/Ruby. Packages with C bindings (numpy, bcrypt,
# sharp) either fail to build or crash at runtime.
#
# WITHOUT IT: Runtime crashes from C extension incompatibility that only
# surface in production. Works in dev, breaks in the container.
#
# FIX: Use a -slim (Debian) variant instead of Alpine
# (e.g., python:3.12-bookworm-slim, node:22-bookworm-slim).
#
# Input: flat array of Dockerfile instructions [{Cmd, Flags, Value, Stage}, ...]

import rego.v1

default _exceptions := []

_exceptions := data.exceptions if {
	data.exceptions
}

# Stacks where musl causes native extension breakage
musl_problem_stacks := {"python", "python3", "uv", "node", "ruby"}

# ── Policy: no Alpine for musl-sensitive stacks ──

deny contains msg if {
	not "dockerfile.base_image" in _exceptions
	some instr in input
	instr.Cmd == "from"
	image := instr.Value[0]

	contains(lower(image), "alpine")

	some stack in musl_problem_stacks
	contains(lower(image), stack)

	msg := sprintf("Alpine base `%s` with %s — musl libc causes compatibility issues with native extensions. Use -slim (Debian) variant instead.", [image, stack])
}
