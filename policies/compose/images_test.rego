package compose.images_test

import rego.v1

import data.compose.images

# ── DENY: build directive present ──

test_build_directive_fires if {
	images.deny with input as {"services": {"app": {"build": "."}}}
}

# ── DENY: mutable tag without pull_policy ──

test_mutable_tag_without_pull_policy_fires if {
	images.deny with input as {"services": {"redis": {"image": "redis:latest"}}}
}

# ── DENY: no tag (implicit :latest) without pull_policy ──

test_no_tag_image_fires if {
	images.deny with input as {"services": {"redis": {"image": "redis"}}}
}

# ── PASS: third-party mutable tag with pull_policy: always ──

test_mutable_tag_with_pull_policy_passes if {
	count(images.deny) == 0 with input as {"services": {"redis": {"image": "redis:latest", "pull_policy": "always"}}}
}

# ── PASS: pinned tag ──

test_pinned_tag_passes if {
	count(images.deny) == 0 with input as {"services": {"app": {"image": "myapp:main-abc1234"}}}
}

# ── DENY: own image with mutable tag ──

test_own_image_mutable_tag_fires if {
	images.deny with input as {"services": {"app": {"image": "ghcr.io/myorg/myapp:latest"}}}
		with data.own_image_prefix as "ghcr.io/myorg/"
}

# ── PASS: own image with pinned tag ──

test_own_image_pinned_passes if {
	count(images.deny) == 0 with input as {"services": {"app": {"image": "ghcr.io/myorg/myapp:main-abc1234"}}}
		with data.own_image_prefix as "ghcr.io/myorg/"
}
