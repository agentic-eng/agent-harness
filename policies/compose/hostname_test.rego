package compose.hostname_test

import rego.v1

import data.compose.hostname

# ── DENY: on dokploy-network without hostname (array format) ──

test_missing_hostname_on_dokploy_network_fires if {
	hostname.deny with input as {"services": {"app": {
		"image": "myapp:v1",
		"networks": ["dokploy-network"],
	}}}
}

# ── DENY: on dokploy-network without hostname (object format) ──

test_missing_hostname_object_network_fires if {
	hostname.deny with input as {"services": {"app": {
		"image": "myapp:v1",
		"networks": {"dokploy-network": {}},
	}}}
}

# ── PASS: on dokploy-network with hostname ──

test_with_hostname_passes if {
	count(hostname.deny) == 0 with input as {"services": {"app": {
		"image": "myapp:v1",
		"hostname": "app",
		"networks": ["dokploy-network"],
	}}}
}

# ── PASS: not on dokploy-network ──

test_internal_network_passes if {
	count(hostname.deny) == 0 with input as {"services": {"app": {
		"image": "myapp:v1",
		"networks": ["internal"],
	}}}
}

# ── PASS: one-shot service exempt ──

test_one_shot_on_dokploy_exempt if {
	count(hostname.deny) == 0 with input as {"services": {
		"migrate": {
			"image": "myapp:v1",
			"networks": ["dokploy-network"],
		},
		"app": {
			"image": "myapp:v1",
			"hostname": "app",
			"networks": ["dokploy-network"],
			"depends_on": {"migrate": {"condition": "service_completed_successfully"}},
		},
	}}
}
