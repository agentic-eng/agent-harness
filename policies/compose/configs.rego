package compose.configs

# COMPOSE CONFIGS — no inline content in configs
#
# WHAT: Ensures top-level `configs:` entries don't use inline `content:` field.
#
# WHY: `docker compose up -d` does not detect changes to inline config content.
# Containers silently keep the stale config from the previous deploy. This is a
# known Docker bug (docker/compose#11900, closed "not planned").
#
# WITHOUT IT: Config changes silently ignored. Service runs with old config after
# redeploy. Debugging is extremely difficult because the config "looks right" in
# the compose file but the container has the old version.
#
# FIX: Use environment variables, envsubst templates baked into the image, or
# `command: sh -c 'cat > /path ...'` pattern instead.
#
# Input: parsed docker-compose YAML

import rego.v1

deny contains msg if {
	some config_name, config in input.configs
	config.content
	msg := sprintf("compose: config '%s' uses inline 'content:' — changes are silently ignored on redeploy (docker/compose#11900)", [config_name])
}
