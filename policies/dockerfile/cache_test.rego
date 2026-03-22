package dockerfile.cache_test

import rego.v1

import data.dockerfile.cache

# ── DENY: dep install without cache mount ──

test_uv_sync_without_cache_fires if {
	cache.deny with input as [
		{"Cmd": "run", "Value": ["uv sync"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

test_pip_install_without_cache_fires if {
	cache.deny with input as [
		{"Cmd": "run", "Value": ["pip install -r requirements.txt"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── PASS: dep install with cache mount ──

test_uv_sync_with_cache_passes if {
	count(cache.deny) == 0 with input as [
		{"Cmd": "run", "Value": ["uv sync"], "Flags": ["--mount=type=cache,target=/root/.cache/uv"], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── PASS: non-dep RUN without cache is fine ──

test_non_dep_run_passes if {
	count(cache.deny) == 0 with input as [
		{"Cmd": "run", "Value": ["echo hello"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}
