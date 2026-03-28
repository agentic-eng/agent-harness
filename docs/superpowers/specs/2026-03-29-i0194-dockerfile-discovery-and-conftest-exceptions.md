# I0194 Response: Dockerfile Discovery, Conftest Exceptions, and Init Improvements

**Date:** 2026-03-29
**Source:** Feedback from aggre project AI agent (I0194)
**Branch:** feat/gitignore-enforcement (current)

## Context

Agent-harness v0.2.0 treats every directory with a Dockerfile as a separate "project" during `init`. In monorepos, Dockerfiles live in `infrastructure/`, `scripts/`, `deploy/` — these are build targets of a single project, not subprojects. This causes scaffolding noise (CLAUDE.md, Makefile, .pre-commit-config.yaml created in every Docker-containing dir) and makes conftest exceptions impossible (no config to attach skip lists to).

## Changes

### 1. Git-aware file discovery (`find_files`)

Replace filesystem walk + hardcoded `SKIP_DIRS` with `git ls-files --cached --others --exclude-standard`.

- New shared utility (e.g., in `workspace.py` or new `git_files.py`)
- `find_files(project_dir, patterns) -> list[Path]`
- Catches tracked, staged, and untracked-but-not-ignored files
- Fallback to filesystem walk for non-git repos
- Replaces `SKIP_DIRS` usage in `workspace.py:discover_roots` and `detect.py:detect_all`
- Git naturally skips nested repos (.worktrees, submodules)

### 2. Dockerfile discovery in Docker preset

`presets/docker/detect.py` gains `find_dockerfiles(project_dir) -> list[Path]` using `find_files`.

- `DockerPreset.run_checks` discovers all Dockerfiles once, passes list to both hadolint and conftest checks
- Each check iterates the list, producing one `CheckResult` per file (e.g., `hadolint:scripts/autonomy/Dockerfile`)
- Compose files stay single (`docker-compose.prod.yml` at root) — no multi-compose discovery

### 3. Conftest exceptions (all presets)

Config schema in `.agent-harness.yml`:

```yaml
docker:
  conftest_skip:
    scripts/autonomy/Dockerfile:
      - dockerfile.user
      - dockerfile.healthcheck
      - dockerfile.cache
```

Flow:
1. Preset reads `config.get("<preset>", {}).get("conftest_skip", {})`
2. For each target file, looks up skip list by relative path
3. Passes `data={"exceptions": [...]}` to `run_conftest`
4. Every Rego policy checks exceptions before firing

Rego pattern (applied to all 6 dockerfile policies, plus compose and dokploy):

```rego
default _exceptions := []
_exceptions := data.exceptions if data.exceptions

deny contains msg if {
    not "dockerfile.user" in _exceptions
    not _has_user_instruction
    msg := "..."
}
```

No policy is non-skippable. The skip is explicit in config, visible in code review.

### 4. Project detection fix (`detect_all`)

A directory is a **project** only if it has a dependency manifest (`pyproject.toml`, `package.json`, `go.mod`). Docker-only directories are not projects — their Dockerfiles are checked by the nearest parent project's Docker preset.

Root directory is always a project.

This means `init` stops scaffolding CLAUDE.md/Makefile/.pre-commit-config.yaml in `infrastructure/staging/` just because it has a Dockerfile.

### 5. Gitignore dedup improvement

`gitignore_setup.py` already does exact dedup (`missing = expected - existing`). Change: group appended patterns by source template instead of one flat block:

```
# Python (added by agent-harness)
*.egg-info/
*.whl

# macOS (added by agent-harness)
.AppleDouble
```

Full .gitignore reorganization (removing stale patterns, rewriting structure) is a judgment call — belongs in skill guidance, not deterministic init.

### 6. Skill doc updates

Add to SKILL.md's audit section:
- "If Makefile has `pip-audit`, `npm audit`, or `gitleaks` targets, replace with `agent-harness security-audit`"
- "After init, review .gitignore — remove stale patterns, reorganize by category"

### 7. Init diagnostic wording (minor)

Improve CLAUDE.md recommendation message from `"mentions lint but not 'make check'"` to `"CLAUDE.md should mention 'make check' as the full quality gate (lint + test + security-audit)"`.

## Design principles applied

- **Init does, skill guides**: init is safe to run blindly. Judgment calls go in skill guidance.
- **All policies are skippable**: we're an enforcer, not a nanny. Explicit skips in config are auditable.
- **Git is the source of truth for file discovery**: no maintaining hardcoded skip lists.
- **A Dockerfile is not a project boundary**: only dependency manifests define subprojects.

## Files to change

| File | Change |
|------|--------|
| `workspace.py` or new `git_files.py` | `find_files()` utility |
| `workspace.py` | `discover_roots` uses `find_files` |
| `detect.py` | `detect_all` uses `find_files`, filters Docker-only dirs |
| `presets/docker/detect.py` | `find_dockerfiles()` using `find_files` |
| `presets/docker/__init__.py` | Wire config + Dockerfile list into checks |
| `presets/docker/conftest_dockerfile_check.py` | Accept Dockerfile list + skip config |
| `presets/docker/hadolint_check.py` | Accept Dockerfile list |
| `conftest.py` | No change (data param already works) |
| `policies/dockerfile/*.rego` (6 files) | Add `_exceptions` guard |
| `policies/compose/*.rego` | Add `_exceptions` guard |
| `policies/dokploy/*.rego` | Add `_exceptions` guard |
| `presets/universal/gitignore_setup.py` | Grouped append by template source |
| `init/scaffold.py` | Skip CLAUDE.md/Makefile/.pre-commit for non-root dirs |
| `skills/agent-harness/SKILL.md` | Redundant tooling + gitignore cleanup guidance |
| `CLAUDE.md` | Already updated with skill layer in Policy Design Strategy |
| Rego `_test.rego` files | Update tests for exceptions |
