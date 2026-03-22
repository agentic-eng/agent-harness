package compose.services_test

import rego.v1

import data.compose.services

# ── DENY: missing healthcheck ──

test_missing_healthcheck_fires if {
	services.deny with input as {"services": {"app": {"image": "myapp:v1", "restart": "unless-stopped"}}}
}

# ── DENY: missing restart policy ──

test_missing_restart_fires if {
	services.deny with input as {"services": {"app": {"image": "myapp:v1"}}}
}

# ── DENY: 0.0.0.0 port binding ──

test_wildcard_port_fires if {
	services.deny with input as {"services": {"app": {
		"image": "myapp:v1",
		"restart": "unless-stopped",
		"healthcheck": {"test": ["CMD", "curl", "-f", "http://localhost/"]},
		"ports": ["0.0.0.0:8080:8080"],
	}}}
}

# ── PASS: one-shot service exempt from healthcheck and restart ──

test_one_shot_exempt_passes if {
	count(services.deny) == 0 with input as {"services": {
		"migrate": {"image": "myapp:v1"},
		"app": {
			"image": "myapp:v1",
			"restart": "unless-stopped",
			"healthcheck": {"test": ["CMD", "curl", "-f", "http://localhost/"]},
			"depends_on": {"migrate": {"condition": "service_completed_successfully"}},
		},
	}}
}

# ── PASS: full valid config ──

test_full_valid_config_passes if {
	count(services.deny) == 0 with input as {"services": {"app": {
		"image": "myapp:v1",
		"restart": "unless-stopped",
		"healthcheck": {"test": ["CMD", "curl", "-f", "http://localhost/"]},
		"ports": ["127.0.0.1:8080:8080"],
	}}}
}
