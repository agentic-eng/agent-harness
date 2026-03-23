# policies/javascript/package_test.rego
package javascript.pkg_test

import data.javascript.pkg
import rego.v1

# ── engines ──

test_missing_engines_denied if {
	count(pkg.deny) > 0 with input as {"name": "x", "version": "1.0.0"}
}

test_engines_present_passes if {
	denials := pkg.deny with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"type": "module",
	}
	count(denials) == 0
}

# ── type: module ──

test_missing_type_warned if {
	count(pkg.warn) > 0 with input as {
		"name": "x",
		"engines": {"node": ">=22"},
	}
}

test_type_module_no_warning if {
	warnings := pkg.warn with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"type": "module",
	}
	count(warnings) == 0
}

# ── wildcard versions ──

test_wildcard_dep_denied if {
	count(pkg.deny) > 0 with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"dependencies": {"bad-pkg": "*"},
	}
}

test_pinned_dep_passes if {
	denials := pkg.deny with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"type": "module",
		"dependencies": {"good-pkg": "^1.2.3"},
	}
	count(denials) == 0
}

test_wildcard_devdep_denied if {
	count(pkg.deny) > 0 with input as {
		"name": "x",
		"engines": {"node": ">=22"},
		"devDependencies": {"bad-dev": "*"},
	}
}
