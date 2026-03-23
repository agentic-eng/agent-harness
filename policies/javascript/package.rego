# policies/javascript/package.rego
package javascript.pkg

# PACKAGE.JSON — engines, type, version hygiene
#
# WHAT: Ensures package.json has `engines` field, `type: "module"`,
# and no wildcard `*` version ranges.
#
# WHY (engines): Without `engines`, the project runs on any Node version.
# Agents and CI may use incompatible versions — code works locally but breaks
# in deployment. `engines` makes version requirements explicit and enforceable.
#
# WHY (type): Node defaults to CommonJS. Mixed ESM/CJS causes confusing errors.
# Explicit `type: "module"` prevents agents from accidentally mixing module systems.
#
# WHY (no wildcards): `*` versions accept anything, including breaking majors.
# Agents run `npm install` and get different versions each time.
#
# WITHOUT IT: "Works on my machine" Node version issues, mixed module system
# errors, non-deterministic dependency resolution.
#
# FIX: Add "engines": {"node": ">=22"}, "type": "module" to package.json.
# Replace * versions with explicit ranges (^x.y.z).
#
# Input: parsed package.json (JSON)

import rego.v1

# ── Policy: engines field must exist ──

deny contains msg if {
	not input.engines
	msg := "package.json: missing 'engines' field — specify Node version to prevent version mismatch"
}

# ── Policy: type should be "module" ──

warn contains msg if {
	not input.type
	msg := "package.json: missing 'type' field — add '\"type\": \"module\"' for explicit ESM"
}

warn contains msg if {
	input.type
	input.type != "module"
	msg := sprintf("package.json: 'type' is '%s', consider 'module' for ESM consistency", [input.type])
}

# ── Policy: no wildcard versions in dependencies ──

deny contains msg if {
	some dep, version in input.dependencies
	version == "*"
	msg := sprintf("package.json: dependency '%s' has wildcard version '*' — pin to explicit range", [dep])
}

deny contains msg if {
	some dep, version in input.devDependencies
	version == "*"
	msg := sprintf("package.json: devDependency '%s' has wildcard version '*' — pin to explicit range", [dep])
}
