package gitignore.secrets

# GITIGNORE — secrets and artifacts must be excluded, per detected stack
#
# WHAT: Ensures .env is always gitignored, plus stack-specific entries
# (.venv/__pycache__ for Python, node_modules/dist for JS).
#
# WHY: Agents create .env files with real secrets. Stack-specific artifacts
# (.venv, node_modules) bloat repos. Without stack awareness, Python entries
# get flagged on JS projects (false positives) and JS entries get missed on
# JS projects (false negatives).
#
# WITHOUT IT: Secrets in git history, false positive noise on wrong stacks,
# missing entries for detected stacks.
#
# FIX: Add the reported entries to .gitignore.
#
# Input: array of [{Kind, Value, Original}] entries
# Data: {stacks: ["python", "javascript", ...]} passed via --data

import rego.v1

# ── Universal: .env must always be gitignored ──

deny contains msg if {
	not _pattern_present(".env")
	msg := ".gitignore: '.env' is not ignored — agents create .env with real secrets"
}

# ── Python stack ──

deny contains msg if {
	"python" in data.stacks
	not _pattern_present(".venv")
	msg := ".gitignore: '.venv' is not ignored — Python virtual environments bloat the repo"
}

deny contains msg if {
	"python" in data.stacks
	not _pattern_present("__pycache__")
	msg := ".gitignore: '__pycache__' is not ignored — compiled bytecode should not be tracked"
}

# ── JavaScript stack ──

deny contains msg if {
	"javascript" in data.stacks
	not _pattern_present("node_modules")
	msg := ".gitignore: 'node_modules' is not ignored — JS dependencies must not be committed"
}

deny contains msg if {
	"javascript" in data.stacks
	not _pattern_present("dist")
	msg := ".gitignore: 'dist' is not ignored — build output should not be tracked"
}

# ── Helper ──

_pattern_present(pattern) if {
	some entry in input
	entry.Kind == "Path"
	contains(entry.Value, pattern)
}
