# Gitignore Enforcement

## Problem

Files listed in `.gitignore` that are already tracked by git remain in the repository.
This is invisible to developers and AI agents alike — `.gitignore` only prevents *new* files
from being tracked, not already-tracked ones. Additionally, `.gitignore` files are often
incomplete, missing common patterns for the project's tech stack or OS.

For agent-harness specifically, this is a credibility problem: a tool that enforces
project hygiene must not ship `.DS_Store` files in its own repo.

## Design

Two complementary features in the universal preset (applies to all projects regardless of stack):

### 1. Lint: Tracked-but-ignored file detection

A new Python check in the universal preset.

**Check (`gitignore_tracked_check.py`):**
- Runs `git ls-files -ci --exclude-standard`
- This reads the git index, not the filesystem — takes milliseconds
- If output is non-empty → `CheckResult(passed=False)`
- Error message lists each offending file and the fix command

**Error format:**
```
Files tracked by git but matching .gitignore:
  src/agent_harness/policies/.DS_Store
Run: git rm --cached <file>  (or: agent-harness fix)
```

**Fix (in `UniversalPreset.run_fix()`):**
- Runs `git rm --cached <file>` for each offending file
- Returns action string: `"gitignore-tracked: removed N files from git tracking"`

**Rationale for unconditional execution:**
The check is milliseconds (git index read). Conditional execution (only when `.gitignore`
changes) saves nothing and introduces a blind spot: files tracked before a `.gitignore`
rule was added would only be caught in the commit window where the rule is added.

### 2. Init: Gitignore completeness check

A new setup check in `UniversalPreset.run_setup()`.

**Detection:**
- Load vendored github/gitignore templates based on detected stacks
- OS globals (macOS, Windows, Linux) always included
- Stack mapping: `"python"` → `Python.gitignore`, `"javascript"` → `Node.gitignore`
- Parse existing `.gitignore` into a set of non-comment, non-blank lines
- Compare against expected patterns from templates
- Missing patterns → `SetupIssue(severity="critical", fix=<append_fn>)`

**Fix behavior:**
- Appends missing patterns at the end of `.gitignore` in a `# Added by agent-harness` block
- Never removes or reorders existing lines
- If no `.gitignore` exists: creates one from full template content

**After appending:** reports any tracked-but-ignored files (reuses lint check logic).

### 3. Vendored templates

**Location:** `src/agent_harness/templates/gitignore/`

**Contents:**
- Language templates: `Python.gitignore`, `Node.gitignore`
- OS globals: `macOS.gitignore`, `Windows.gitignore`, `Linux.gitignore`
- Only for stacks agent-harness already supports
- `SOURCE.md` with attribution to github/gitignore and license info

**Refresh:** Manual script `scripts/update-gitignore-templates.sh` pulls latest from
GitHub API. No CI automation — templates change rarely.

**Stack-to-template mapping:**

| Stack | Template |
|-------|----------|
| `python` | `Python.gitignore` |
| `javascript` | `Node.gitignore` |
| `docker` | (no language-specific template) |
| (always) | `macOS.gitignore`, `Windows.gitignore`, `Linux.gitignore` |

## Integration

No new presets, no new dependencies, no new external tools.

| Component | Location | Type |
|-----------|----------|------|
| Tracked-file check | `presets/universal/gitignore_tracked_check.py` | `CheckResult` |
| Tracked-file fix | `UniversalPreset.run_fix()` | `git rm --cached` |
| Completeness check | `UniversalPreset.run_setup()` | `SetupIssue` with auto-fix |
| Templates | `templates/gitignore/` | Vendored text files |
| Refresh script | `scripts/update-gitignore-templates.sh` | Curl from GitHub API |

## What this does NOT change

- Registry, preset interface, config loading
- Rego policies (existing gitignore conftest check validates `.gitignore` *content rules*
  like `.env` presence — complementary, not overlapping)
- Existing `.gitignore` line ordering or user-added patterns

## Scope boundary

Agent-harness checks gitignore completeness and tracked-file hygiene. It does not become
a gitignore generator — it uses community templates as a reference set and only appends
missing patterns.
