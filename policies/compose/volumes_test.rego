package compose.volumes_test

import data.compose.volumes
import rego.v1

test_bind_mount_relative_denied if {
	count(volumes.deny) > 0 with input as {"services": {"app": {"volumes": ["./config:/etc/app"]}}}
}

test_bind_mount_absolute_denied if {
	count(volumes.deny) > 0 with input as {"services": {"app": {"volumes": ["/host/path:/container"]}}}
}

test_named_volume_passes if {
	count(volumes.deny) == 0 with input as {"services": {"db": {"volumes": ["postgres-data:/var/lib/postgresql/data"]}}}
}

test_no_volumes_passes if {
	count(volumes.deny) == 0 with input as {"services": {"app": {"image": "myapp:1.0"}}}
}

test_service_without_volumes_key_passes if {
	count(volumes.deny) == 0 with input as {"services": {"app": {}}}
}
