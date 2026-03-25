package python.coverage

# COVERAGE CONFIG — show gaps, not green files
#
# WHAT: Ensures coverage output is optimized so agents see gaps, not noise.
# These are gates that must exist. Value judgments are handled by init.
#
# LINT RULES (deny): Is coverage objectively misconfigured?
# INIT CHECKS (Python): Is it optimally configured? Fix it.
#
# Input: parsed pyproject.toml (TOML -> JSON)

import rego.v1

# ── Policy: skip_covered = true ──
# Without this, agent sees 50+ fully-covered files drowning 2 that need work.

deny contains msg if {
	report := input.tool.coverage.report
	not report.skip_covered
	msg := "coverage.report: missing 'skip_covered' — set to true so agents only see files with gaps"
}

deny contains msg if {
	report := input.tool.coverage.report
	report.skip_covered == false
	msg := "coverage.report: skip_covered is false — set to true so agents only see files with gaps"
}

# ── Policy: branch coverage enabled ──
# Line-only coverage misses untested if/else branches.

deny contains msg if {
	run := input.tool.coverage.run
	not run.branch
	msg := "coverage.run: missing 'branch' — set to true to catch untested if/else branches"
}

deny contains msg if {
	run := input.tool.coverage.run
	run.branch == false
	msg := "coverage.run: branch is false — set to true to catch untested if/else branches"
}
