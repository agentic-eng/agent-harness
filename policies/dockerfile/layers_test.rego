package dockerfile.layers_test

import rego.v1

import data.dockerfile.layers

# ── DENY: broad COPY before dependency install ──

test_copy_dot_before_deps_fires if {
	layers.deny with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "copy", "Value": [".", "."], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "run", "Value": ["uv sync"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

test_copy_src_dir_before_deps_fires if {
	layers.deny with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "copy", "Value": ["src", "/app/src"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "run", "Value": ["pip install -r requirements.txt"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── PASS: correct order — deps first, then source ──

test_deps_before_source_passes if {
	count(layers.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "copy", "Value": ["pyproject.toml", "uv.lock", "./"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "run", "Value": ["uv sync"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
		{"Cmd": "copy", "Value": [".", "."], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── PASS: multi-stage COPY --from does not fire ──

test_copy_from_stage_passes if {
	count(layers.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["python:3.12-slim"], "Flags": [], "Stage": 1, "SubCmd": "", "JSON": false},
		{"Cmd": "copy", "Value": ["/app", "/app"], "Flags": ["--from=builder"], "Stage": 1, "SubCmd": "", "JSON": false},
		{"Cmd": "run", "Value": ["uv sync"], "Flags": [], "Stage": 1, "SubCmd": "", "JSON": false},
	]
}
