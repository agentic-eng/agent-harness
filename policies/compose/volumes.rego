package compose.volumes

# COMPOSE VOLUMES — no bind mounts in production
#
# WHAT: Ensures no service uses bind mount volumes (host path:container path).
#
# WHY: Bind mounts require the file/directory to exist at the exact path on the
# host. This breaks with: (a) remote Docker hosts, (b) deployment platforms that
# wipe working directories on redeploy, (c) any system that deploys the compose
# file without the surrounding directory structure.
#
# WITHOUT IT: Deployments silently fail or use stale config files from previous
# deploys. Works locally, breaks in production. Debugging takes hours.
#
# FIX: Use named volumes for persistent data, envsubst templates baked into
# images for config, or `command: sh -c 'cat > /path ...'` for third-party images.
#
# Input: parsed docker-compose YAML

import rego.v1

deny contains msg if {
	some service_name, service in input.services
	some volume in service.volumes
	_is_bind_mount(volume)
	msg := sprintf("compose: service '%s' uses bind mount volume '%s' — use named volumes or bake config into the image", [service_name, volume])
}

_is_bind_mount(volume) if {
	is_string(volume)
	contains(volume, ":")
	parts := split(volume, ":")
	count(parts) >= 2
	# Host path starts with . or / — that's a bind mount
	startswith(parts[0], ".")
}

_is_bind_mount(volume) if {
	is_string(volume)
	contains(volume, ":")
	parts := split(volume, ":")
	count(parts) >= 2
	startswith(parts[0], "/")
}
