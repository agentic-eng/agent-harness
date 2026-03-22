package dockerfile.base_image_test

import rego.v1

import data.dockerfile.base_image

# ── DENY: Alpine with musl-sensitive stacks ──

test_python_alpine_fires if {
	base_image.deny with input as [
		{"Cmd": "from", "Value": ["python:3.12-alpine"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

test_node_alpine_fires if {
	base_image.deny with input as [
		{"Cmd": "from", "Value": ["node:22-alpine"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── PASS: Alpine with non-musl-sensitive stack ──

test_go_alpine_passes if {
	count(base_image.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["golang:1.22-alpine"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}

# ── PASS: slim variant ──

test_python_slim_passes if {
	count(base_image.deny) == 0 with input as [
		{"Cmd": "from", "Value": ["python:3.12-bookworm-slim"], "Flags": [], "Stage": 0, "SubCmd": "", "JSON": false},
	]
}
