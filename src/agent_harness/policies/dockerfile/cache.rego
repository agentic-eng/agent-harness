package dockerfile.cache

# CACHE MOUNT — persist dependency caches between builds
#
# WHAT: Ensures dependency install commands use --mount=type=cache.
#
# WHY: Without cache mounting, dependency caches are discarded between builds.
# Agents don't know to add --mount=type=cache flags. Each rebuild downloads
# all packages from the internet even when nothing changed.
#
# WITHOUT IT: Every rebuild downloads all packages from the internet.
# pip/npm/cargo caches vanish after each build layer completes.
#
# FIX: Add --mount=type=cache,target=<cache-dir> to RUN instructions
# (e.g., /root/.cache/uv for uv, /root/.cache/pip for pip, /root/.npm for npm).
#
# Input: flat array of Dockerfile instructions [{Cmd, Flags, Value, Stage}, ...]

import rego.v1

default _exceptions := []

_exceptions := data.exceptions if {
	data.exceptions
}

dep_install_pattern := `(uv sync|pip install|pip3 install|poetry install|pdm install|npm ci|npm install|yarn install|pnpm install|bun install|go mod download|cargo build|cargo install|bundle install|gem install)`

# ── Policy: dep install must use --mount=type=cache ──

deny contains msg if {
	not "dockerfile.cache" in _exceptions
	some instr in input
	instr.Cmd == "run"

	some val in instr.Value
	regex.match(dep_install_pattern, val)

	not _has_cache_mount(instr)

	cmd := regex.find_n(dep_install_pattern, val, 1)[0]
	msg := sprintf("`%s` without --mount=type=cache — dependency cache is discarded between builds, slowing rebuilds", [cmd])
}

_has_cache_mount(instr) if {
	some flag in instr.Flags
	contains(flag, "mount=type=cache")
}
