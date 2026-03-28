package dockerfile.healthcheck

# HEALTHCHECK — orchestrator liveness detection
#
# WHAT: Ensures at least one HEALTHCHECK instruction exists in the Dockerfile.
#
# WHY: Without healthchecks, orchestrators can't detect unhealthy containers.
# Load balancers route traffic to dead services. Deployments report success
# while the app crashes in a loop. CIS Docker Benchmark 4.6 / Trivy DS-0026.
#
# WITHOUT IT: Silent failures — service is down but everything reports green.
# Rolling deployments replace healthy containers with broken ones.
#
# FIX: Add `HEALTHCHECK CMD curl -f http://localhost:<port>/health || exit 1`
# (or a similar probe) to the Dockerfile.
#
# Input: flat array of Dockerfile instructions [{Cmd, Flags, Value, Stage}, ...]

import rego.v1

default _exceptions := []

_exceptions := data.exceptions if {
	data.exceptions
}

# ── Policy: must have HEALTHCHECK instruction ──

deny contains msg if {
	not "dockerfile.healthcheck" in _exceptions
	not _has_healthcheck
	msg := "Dockerfile has no HEALTHCHECK instruction — orchestrators can't detect unhealthy containers. Add 'HEALTHCHECK CMD curl -f http://localhost/ || exit 1' or similar."
}

_has_healthcheck if {
	some instr in input
	instr.Cmd == "healthcheck"
}
