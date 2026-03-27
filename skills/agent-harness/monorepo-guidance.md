# Monorepo Guidance

Common issues in monorepos that can't be caught by lint — they require understanding how git and tooling interact with directory structure.

---

## Subproject pre-commit configs are redundant

Git hooks run from the repo root. Only the **root** `.pre-commit-config.yaml` is triggered during `git commit`. Pre-commit configs inside subproject directories are never executed automatically.

**The trap:** An agent audits a subproject, sees it has no `.pre-commit-config.yaml` (or an incomplete one), and adds/fixes one. This looks productive but does nothing — the file is dead code that adds confusion.

**What to do:**
- Do NOT create or modify `.pre-commit-config.yaml` in subproject directories
- If subproject pre-commit configs already exist, flag them as redundant and remove them
- All pre-commit hooks belong in the root `.pre-commit-config.yaml` only
- If someone needs to run checks from a subproject directory, `make lint` (delegating to `agent-harness lint`) is the correct mechanism — not pre-commit

**Exception:** Subprojects that are independently cloned repos (git submodules, sparse checkouts) may need their own hooks. This is rare.
