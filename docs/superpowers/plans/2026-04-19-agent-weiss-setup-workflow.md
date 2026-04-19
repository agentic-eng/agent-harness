# agent-weiss Setup Workflow & Approval UX (Plan 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the testable orchestration layer for the setup phase (gap analysis → batched proposals → verb parser → apply → backup → dry-run → state update), and wire it into `skill.md`. Reconcile UX adopts the same batching pattern. Plan 1 hardening items folded into a preflight task.

**Architecture:** All orchestration logic lives under `src/agent_weiss/lib/setup/` (new package). Each piece is a small testable module. Skill.md is the conductor that calls them in sequence. The interactive prompt loop (read user input, parse, dispatch) happens in skill.md natural-language; Python provides primitives.

**Tech Stack:** existing (Python 3.12+, pytest, ruamel.yaml — no new deps).

**Repository:** `/Users/iorlas/Workspaces/agent-weiss` (Plan 2 complete; tagged `control-library` at commit 764df8c, 127 tests).

**Spec / roadmap:**
- `docs/superpowers/specs/2026-04-14-agent-weiss-design.md`
- `docs/superpowers/plans/2026-04-14-agent-weiss-roadmap.md` (cross-cutting decisions)
- `docs/superpowers/plans/2026-04-14-agent-weiss-foundations.md` (Plan 1)
- `docs/superpowers/plans/2026-04-18-agent-weiss-control-library.md` (Plan 2)

**Plan scope (in):**
- Hardening preflight (4 small Plan 1 review fixes)
- `Proposal`, `Decision`, `ActionKind` types
- `compute_proposals(project_root, bundle_root, profiles, controls)` gap analysis
- `batch_by_domain(proposals)` + numbered rendering helper
- Verb parser (`approve all`, `approve <domain>`, `<numbers>`, `skip <numbers> [reason]`, `explain <N>`, `dry-run`, `cancel`)
- Backup writer to `.agent-weiss/backups/<timestamp>/` (built now; used by future install_file/merge_fragment paths)
- `apply_proposal` — `manual_action` path (records "user confirmed handled" or override-with-reason in state)
- Dry-run report generator (writes `.agent-weiss/dry-run-<timestamp>.md`, exits)
- depends_on cascade resolver
- Reconcile UX: revisit Plan 1's reconcile detector and add prompt-batching wrapper using the same Decision verbs
- State extension: typed `overrides: dict[str, OverrideEntry]` field
- Skill.md updates wiring the helpers into the actual setup loop

**Plan scope (out — handled later):**
- `install_file` action path (deferred — no current control ships an installable artifact)
- `merge_fragment` action path (deferred — needs spec clarification on Plan 2 prescribed.yaml retrofit; format-aware TOML/JSON/YAML mergers are nontrivial)
- **Diff preview generation** (deferred together with install/merge — there's nothing to diff in MANUAL_ACTION mode since the skill doesn't write project files; the user reviews `instruct.md` directly)
- Verify workflow + scoring (Plan 4)
- Distribution packaging (Plan 5)
- Drift refresh UX (Plan 6)

**Scope rationale:** Plan 2's controls are all detection-only — they enforce config you've already added; none ship `config_fragment` payloads or template files. So Plan 3's runtime story is "for any failing control, surface its `instruct.md`, ask the user to confirm done or override with reason, record decision in state." The orchestration primitives (verb parser, batching, backup writer, dry-run report) are built fully so future plans can plug `install_file` and `merge_fragment` action kinds in without re-architecting.

---

## Pause points

- **After Task 1:** hardening preflight done. 127→131 tests (4 new for the fixes).
- **After Task 5:** verb parser shipped — half the orchestration done.
- **After Task 9:** dry-run + cascade done; setup primitives complete.
- **After Task 11:** reconcile UX integrated. Skill.md updates pending.
- **After Task 13:** Plan 3 complete, tagged.

---

## Task 1: Hardening preflight (Plan 1 review fixes)

**Files:**
- Modify: `src/agent_weiss/lib/state.py` (deepcopy _raw + schema_version field)
- Modify: `src/agent_weiss/lib/reconcile.py` (recursive orphan scan)
- Modify: `tests/test_state.py` (cover new schema_version + deepcopy behavior)
- Modify: `tests/test_reconcile.py` (cover recursive orphan scan)
- Modify: `tests/test_control_completeness.py` (id-vs-path consistency check)

These four fixes were flagged in Plan 1's final review. Address them as one preflight task before adding new functionality.

- [ ] **Step 1: Add failing tests for hardening fixes**

Append to `/Users/iorlas/Workspaces/agent-weiss/tests/test_state.py`:

```python
import copy
from agent_weiss.lib.state import State, PrescribedFileEntry, read_state, write_state, SCHEMA_VERSION


def test_state_schema_version_round_trips(tmp_path):
    """State.schema_version is read from disk and re-written on round-trip."""
    state_path = tmp_path / ".agent-weiss.yaml"
    state_path.write_text("version: 1\nbundle_version: '0.0.1'\nprofiles: []\n")
    state = read_state(tmp_path)
    assert state.schema_version == 1
    write_state(tmp_path, state)
    re_read = read_state(tmp_path)
    assert re_read.schema_version == 1


def test_state_unknown_schema_version_raises(tmp_path):
    """Reading a state file with a schema_version newer than supported raises."""
    state_path = tmp_path / ".agent-weiss.yaml"
    state_path.write_text(f"version: {SCHEMA_VERSION + 1}\nprofiles: []\n")
    import pytest
    with pytest.raises(ValueError, match="schema_version"):
        read_state(tmp_path)


def test_write_state_does_not_mutate_raw(tmp_path):
    """Calling write_state should not mutate state._raw nested values (deepcopy guarantee)."""
    state_path = tmp_path / ".agent-weiss.yaml"
    state_path.write_text(
        "version: 1\n"
        "profiles: []\n"
        "future_block:\n"
        "  nested:\n"
        "    key: original_value\n"
    )
    state = read_state(tmp_path)
    # Snapshot _raw before write.
    raw_before = copy.deepcopy(state._raw)
    write_state(tmp_path, state)
    # state._raw must not have been mutated.
    assert state._raw == raw_before
```

Append to `/Users/iorlas/Workspaces/agent-weiss/tests/test_reconcile.py`:

```python
def test_orphan_scan_is_recursive(tmp_path):
    """Files in nested subdirs of .agent-weiss/policies/ are detected as orphans."""
    nested = tmp_path / ".agent-weiss" / "policies" / "subdir"
    nested.mkdir(parents=True)
    (nested / "nested.rego").write_bytes(b"package nested\n")
    _setup_project_with_state(tmp_path, {})
    report = reconcile(tmp_path)
    assert any(a.kind == "orphan" and a.path.endswith("nested.rego") for a in report.anomalies)
```

Append to `/Users/iorlas/Workspaces/agent-weiss/tests/test_control_completeness.py`:

```python
@pytest.mark.parametrize("control_dir", _all_control_dirs(), ids=lambda p: str(p.relative_to(PROFILES)))
def test_control_id_matches_path(control_dir: Path):
    """prescribed.yaml id must match the directory path: profile.domain.control."""
    p = control_dir / "prescribed.yaml"
    yaml = YAML(typ="safe")
    data = yaml.load(p)
    relative = control_dir.relative_to(PROFILES)
    parts = relative.parts  # ('profile', 'domains', 'domain', 'controls', 'control')
    expected_id = f"{parts[0]}.{parts[2]}.{parts[4]}"
    assert data["id"] == expected_id, (
        f"prescribed.yaml id={data['id']!r} doesn't match path-derived id={expected_id!r}"
    )
```

- [ ] **Step 2: Run tests to verify the new ones FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest -v
```

Expected: 4 new tests fail (3 in test_state.py, 1 in test_reconcile.py — the id-vs-path test should pass already if all controls are correctly named, which they are after Plan 2). Existing 127 tests still pass.

If `test_control_id_matches_path` passes immediately, that's fine — it just becomes a regression-prevention test for future controls.

- [ ] **Step 3: Apply state.py fixes**

In `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/state.py`:

Add `import copy` at top (after `from __future__ import annotations`).

Update the `State` dataclass to add `schema_version`:
```python
@dataclass
class State:
    """In-memory representation of .agent-weiss.yaml.

    Only the fields the skeleton reads are typed here; unknown top-level keys
    are preserved verbatim via the _raw shadow dict for forward compatibility.
    """
    bundle_version: str | None = None
    schema_version: int = SCHEMA_VERSION
    profiles: list[str] = field(default_factory=list)
    prescribed_files: dict[str, PrescribedFileEntry] = field(default_factory=dict)
    _raw: dict = field(default_factory=dict, repr=False)
```

Update `read_state` to read and validate schema_version:
```python
def read_state(project_root: Path) -> State:
    """Read .agent-weiss.yaml from project root. Returns empty State if missing.

    Raises ValueError if state file's schema_version is newer than this code supports.
    """
    path = project_root / STATE_FILENAME
    if not path.exists():
        return State()

    yaml = _yaml()
    raw = yaml.load(path) or {}

    raw_version = raw.get("version", SCHEMA_VERSION)
    if raw_version > SCHEMA_VERSION:
        raise ValueError(
            f"schema_version {raw_version} is newer than supported "
            f"({SCHEMA_VERSION}). Upgrade agent-weiss."
        )

    pf = {}
    for key, entry in (raw.get("prescribed_files") or {}).items():
        pf[str(key)] = PrescribedFileEntry(
            sha256=str(entry["sha256"]),
            bundle_path=str(entry["bundle_path"]),
            last_synced=str(entry["last_synced"]),
        )

    return State(
        bundle_version=raw.get("bundle_version"),
        schema_version=int(raw_version),
        profiles=list(raw.get("profiles") or []),
        prescribed_files=pf,
        _raw=dict(raw),
    )
```

Update `write_state` to deepcopy `_raw` so writes don't mutate:
```python
def write_state(project_root: Path, state: State) -> None:
    """Write State back to .agent-weiss.yaml, preserving unknown keys."""
    path = project_root / STATE_FILENAME
    yaml = _yaml()

    out = copy.deepcopy(state._raw)
    out["version"] = SCHEMA_VERSION
    if state.bundle_version is not None:
        out["bundle_version"] = state.bundle_version
    out["profiles"] = state.profiles
    out["prescribed_files"] = {
        path_key: {
            "sha256": entry.sha256,
            "bundle_path": entry.bundle_path,
            "last_synced": entry.last_synced,
        }
        for path_key, entry in state.prescribed_files.items()
    }

    with path.open("w") as f:
        yaml.dump(out, f)
```

- [ ] **Step 4: Apply reconcile.py fix**

In `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/reconcile.py`, change the orphan scan from `iterdir()` to recursive `rglob()`:

Replace the orphan-detection block:
```python
    # 2. Detect orphans (in policies dir or any subdir, not tracked).
    policies_dir = project_root / POLICIES_DIR
    if policies_dir.exists():
        for entry_path in policies_dir.rglob("*"):
            if not entry_path.is_file():
                continue
            relative_path = str(entry_path.relative_to(project_root))
            if relative_path not in state.prescribed_files:
                report.anomalies.append(Anomaly(
                    kind="orphan",
                    path=relative_path,
                    detail="present on disk, not in prescribed_files",
                ))
```

- [ ] **Step 5: Run all tests to verify they PASS**

```bash
uv run pytest -v
```

Expected: 131 tests pass (127 prior + 3 new in state + 1 new in reconcile; the id-vs-path completeness test runs against all 16 controls so it adds 16 parametrized cases). Adjust the expected count based on actual collected count — don't worry about exact arithmetic, just confirm zero failures.

- [ ] **Step 6: Verify Rego policies still pass conftest verify**

```bash
for dir in profiles/universal/domains/security/controls/gitignore-secrets \
           profiles/python/domains/quality/controls/ruff-config \
           profiles/python/domains/testing/controls/pytest-config \
           profiles/python/domains/testing/controls/coverage-config \
           profiles/python/domains/testing/controls/test-isolation \
           profiles/typescript/domains/project-structure/controls/package-json; do
  conftest verify --policy "$dir/" || exit 1
done
```

Expected: all 6 directories report `N tests, N passed`.

- [ ] **Step 7: Commit**

```bash
git add src/agent_weiss/lib/state.py src/agent_weiss/lib/reconcile.py tests/
git commit -m "fix: hardening preflight from Plan 1 review

- state.py: deepcopy _raw on write to prevent multi-write drift
- state.py: typed schema_version field, validate on read
- reconcile.py: recursive orphan scan (rglob, not iterdir)
- tests/test_control_completeness.py: assert prescribed.yaml id matches dir path"
git push
```

---

## Task 2: Setup package skeleton + types

**Files:**
- Create: `src/agent_weiss/lib/setup/__init__.py`
- Create: `src/agent_weiss/lib/setup/types.py`
- Create: `tests/test_setup_types.py`

Establish the `setup/` package with the core data types every subsequent task uses. All types are frozen dataclasses (immutable, hashable) for safety in batched contexts.

- [ ] **Step 1: Write failing tests**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_setup_types.py`:

```python
"""Tests for setup orchestration types."""
import pytest
from agent_weiss.lib.setup.types import (
    ActionKind,
    Proposal,
    Decision,
    OverrideEntry,
)


def test_action_kind_enum():
    assert ActionKind.MANUAL_ACTION.value == "manual_action"
    assert ActionKind.INSTALL_FILE.value == "install_file"
    assert ActionKind.MERGE_FRAGMENT.value == "merge_fragment"


def test_proposal_is_frozen():
    p = Proposal(
        control_id="universal.docs.agents-md-present",
        profile="universal",
        domain="docs",
        action_kind=ActionKind.MANUAL_ACTION,
        summary="Create AGENTS.md at repo root",
        instruct_path=None,
        depends_on=[],
    )
    with pytest.raises((AttributeError, TypeError)):
        p.summary = "mutated"


def test_decision_defaults():
    d = Decision()
    assert d.approve_all is False
    assert d.approve_indices == []
    assert d.skip_indices == []
    assert d.skip_reasons == {}
    assert d.approve_domains == []
    assert d.explain_index is None
    assert d.dry_run is False
    assert d.cancel is False


def test_decision_carries_full_choice_set():
    d = Decision(
        approve_indices=[1, 3, 5],
        skip_indices=[2],
        skip_reasons={2: "we use mypy not ty"},
        explain_index=4,
    )
    assert d.approve_indices == [1, 3, 5]
    assert d.skip_reasons[2] == "we use mypy not ty"
    assert d.explain_index == 4


def test_override_entry():
    o = OverrideEntry(reason="we use mypy", decided_at="2026-04-19")
    assert o.reason == "we use mypy"
    assert o.decided_at == "2026-04-19"
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_setup_types.py -v
```

Expected: 5 tests fail on import.

- [ ] **Step 3: Implement the package**

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/setup/__init__.py`:
```python
"""Setup workflow orchestration helpers.

The skill.md scaffold from Plan 1 invokes these helpers in sequence:
1. compute_proposals — gap-analyze each control, return Proposals
2. batch_by_domain — group proposals by domain for the user prompt
3. parse_verb — turn user input into a Decision
4. apply_proposal — execute approved actions (manual_action: record handled;
   install_file/merge_fragment: stubs for v2)
5. write_dry_run_report — generate the dry-run markdown
"""
```

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/setup/types.py`:
```python
"""Core data types for the setup orchestration layer."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ActionKind(Enum):
    """What the setup phase would do for this control if approved.

    MANUAL_ACTION: the only path used in v1 — show instruct.md, ask the user
        to fix it themselves and confirm done. No automatic file changes.
    INSTALL_FILE: stub — copy a bundle file into the project. Reserved for
        future plans when controls ship installable artifacts.
    MERGE_FRAGMENT: stub — merge a config fragment into a target config file.
        Reserved for future plans when controls ship config_fragment payloads
        and format-aware mergers exist.
    """
    MANUAL_ACTION = "manual_action"
    INSTALL_FILE = "install_file"
    MERGE_FRAGMENT = "merge_fragment"


@dataclass(frozen=True)
class Proposal:
    """One proposed setup action for a single control.

    Plan 3 only emits MANUAL_ACTION proposals. The other action_kind values
    are present so the data model doesn't churn when later plans add them.
    """
    control_id: str
    profile: str
    domain: str
    action_kind: ActionKind
    summary: str
    instruct_path: Path | None = None
    depends_on: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Decision:
    """Parsed user decision over a batch of proposals.

    Indices are 1-based as displayed to the user.
    Use `approve_all=True` for "approve all" or `approve_domains=[...]` for
    "approve <domain>". `approve_indices` and `skip_indices` carry explicit
    per-item picks. `explain_index` (if set) means the user asked to explain
    one item; the skill should re-prompt afterward.
    """
    approve_all: bool = False
    approve_domains: list[str] = field(default_factory=list)
    approve_indices: list[int] = field(default_factory=list)
    skip_indices: list[int] = field(default_factory=list)
    skip_reasons: dict[int, str] = field(default_factory=dict)
    explain_index: int | None = None
    dry_run: bool = False
    cancel: bool = False


@dataclass
class OverrideEntry:
    """A control was deliberately declined with a stated reason.

    Recorded under State.overrides[control_id]. Counts as 'pass' in the Setup
    score (Plan 4) per the roadmap's 'Override = pass' rule.
    """
    reason: str
    decided_at: str  # ISO date
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
uv run pytest tests/test_setup_types.py -v
uv run pytest -v
```

Expected: 5 new pass; full suite count grows by 5.

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/setup/ tests/test_setup_types.py
git commit -m "feat: setup orchestration types (Proposal, Decision, OverrideEntry, ActionKind)"
git push
```

---

## Task 3: Extend State with overrides

**Files:**
- Modify: `src/agent_weiss/lib/state.py` (add `overrides` field + read/write)
- Modify: `tests/test_state.py` (cover overrides round-trip)

The setup loop records declined controls (with reason) as overrides. Per the spec, `overrides` lives at the top level of `.agent-weiss.yaml` (the spec uses `prescribed.<control>.overrides` as the path; we flatten to a top-level `overrides` map for typing simplicity).

- [ ] **Step 1: Write failing tests**

Append to `/Users/iorlas/Workspaces/agent-weiss/tests/test_state.py`:

```python
from agent_weiss.lib.setup.types import OverrideEntry


def test_state_overrides_round_trip(tmp_path):
    """Overrides written to state are re-read with same shape."""
    from agent_weiss.lib.state import State, write_state, read_state
    state = State(
        bundle_version="0.0.1",
        profiles=["python"],
        overrides={
            "python.quality.ty-config": OverrideEntry(
                reason="we use mypy",
                decided_at="2026-04-19",
            ),
        },
    )
    write_state(tmp_path, state)
    loaded = read_state(tmp_path)
    assert "python.quality.ty-config" in loaded.overrides
    assert loaded.overrides["python.quality.ty-config"].reason == "we use mypy"
    assert loaded.overrides["python.quality.ty-config"].decided_at == "2026-04-19"


def test_state_overrides_default_empty(tmp_path):
    """A fresh state has empty overrides."""
    from agent_weiss.lib.state import read_state
    assert read_state(tmp_path).overrides == {}
```

- [ ] **Step 2: Run test — verify FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_state.py -v
```

Expected: 2 new tests fail.

- [ ] **Step 3: Update state.py**

In `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/state.py`:

Add import at top:
```python
from agent_weiss.lib.setup.types import OverrideEntry
```

Add to `State` dataclass:
```python
    overrides: dict[str, OverrideEntry] = field(default_factory=dict)
```

In `read_state`, after building `pf`, also build `overrides`:
```python
    overrides = {}
    for control_id, entry in (raw.get("overrides") or {}).items():
        overrides[str(control_id)] = OverrideEntry(
            reason=str(entry["reason"]),
            decided_at=str(entry["decided_at"]),
        )
```

Pass `overrides=overrides` to `State(...)`.

In `write_state`, add to `out`:
```python
    out["overrides"] = {
        control_id: {"reason": entry.reason, "decided_at": entry.decided_at}
        for control_id, entry in state.overrides.items()
    }
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
uv run pytest -v
```

Expected: 2 more tests pass; suite count grows.

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/state.py tests/test_state.py
git commit -m "feat: typed overrides field on State"
git push
```

---

## Task 4: Gap analysis — `compute_proposals`

**Files:**
- Create: `src/agent_weiss/lib/setup/gap.py`
- Create: `tests/test_setup_gap.py`

Walk every control under matching profiles, decide if it needs user attention, and emit a Proposal. In Plan 3 (manual_action only), every control that isn't already overridden becomes a MANUAL_ACTION proposal. Plan 4 will refine "needs attention" to be driven by check.sh results; for now, "every applicable control" is the v1 conservative read.

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_setup_gap.py`:

```python
"""Tests for compute_proposals gap analysis."""
from pathlib import Path
import pytest

from agent_weiss.lib.setup.gap import compute_proposals
from agent_weiss.lib.setup.types import Proposal, ActionKind, OverrideEntry
from agent_weiss.lib.state import State


REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE = REPO_ROOT  # use the agent-weiss repo itself as bundle for tests


def test_compute_proposals_for_universal_profile_only():
    """With profiles=['universal'], proposals cover the 8 universal controls only."""
    state = State(profiles=["universal"])
    proposals = compute_proposals(
        project_root=Path("/tmp/fake-project"),
        bundle_root=BUNDLE,
        state=state,
    )
    profiles = {p.profile for p in proposals}
    assert profiles == {"universal"}
    # Plan 1's agents-md-present + Plan 2's 7 universal controls = 8
    assert len(proposals) == 8


def test_compute_proposals_for_python_profile():
    """profiles=['python'] returns exactly the 5 python controls."""
    state = State(profiles=["python"])
    proposals = compute_proposals(
        project_root=Path("/tmp/fake-project"),
        bundle_root=BUNDLE,
        state=state,
    )
    profiles = {p.profile for p in proposals}
    assert profiles == {"python"}
    assert len(proposals) == 5


def test_compute_proposals_skips_overridden():
    """Controls already in state.overrides are excluded from proposals."""
    state = State(
        profiles=["python"],
        overrides={
            "python.quality.ty-config": OverrideEntry(
                reason="we use mypy",
                decided_at="2026-04-19",
            ),
        },
    )
    proposals = compute_proposals(
        project_root=Path("/tmp/fake-project"),
        bundle_root=BUNDLE,
        state=state,
    )
    ids = {p.control_id for p in proposals}
    assert "python.quality.ty-config" not in ids
    assert len(proposals) == 4


def test_proposals_are_manual_action_in_v1():
    """Plan 3 emits only MANUAL_ACTION proposals."""
    state = State(profiles=["universal"])
    proposals = compute_proposals(
        project_root=Path("/tmp/fake-project"),
        bundle_root=BUNDLE,
        state=state,
    )
    assert all(p.action_kind == ActionKind.MANUAL_ACTION for p in proposals)


def test_proposal_carries_instruct_path():
    """Each proposal points at its control's instruct.md."""
    state = State(profiles=["universal"])
    proposals = compute_proposals(
        project_root=Path("/tmp/fake-project"),
        bundle_root=BUNDLE,
        state=state,
    )
    for p in proposals:
        assert p.instruct_path is not None
        assert p.instruct_path.exists(), f"missing {p.instruct_path}"
        assert p.instruct_path.name == "instruct.md"


def test_proposal_carries_depends_on():
    """If prescribed.yaml declares depends_on, the proposal carries it through."""
    # None of v1 controls declare depends_on, so this just verifies the field
    # is populated (empty list is fine).
    state = State(profiles=["python"])
    proposals = compute_proposals(
        project_root=Path("/tmp/fake-project"),
        bundle_root=BUNDLE,
        state=state,
    )
    for p in proposals:
        assert isinstance(p.depends_on, list)
```

- [ ] **Step 2: Run test — FAIL expected**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_setup_gap.py -v
```

Expected: 6 tests fail on import.

- [ ] **Step 3: Implement gap.py**

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/setup/gap.py`:

```python
"""Gap analysis: walk applicable controls, emit Proposals.

In v1 (Plan 3), every applicable control that isn't already overridden becomes
a MANUAL_ACTION proposal. Plan 4 will tighten this to be driven by check.sh
results (only failing or setup-unmet controls become proposals).
"""
from __future__ import annotations
from pathlib import Path

from ruamel.yaml import YAML

from agent_weiss.lib.state import State
from agent_weiss.lib.schemas import validate_prescribed
from agent_weiss.lib.setup.types import Proposal, ActionKind


def compute_proposals(
    project_root: Path,
    bundle_root: Path,
    state: State,
) -> list[Proposal]:
    """Walk the bundle's profiles tree and emit a Proposal per applicable control.

    Skips controls whose id is already in state.overrides.
    """
    yaml = YAML(typ="safe")
    proposals: list[Proposal] = []

    profiles_root = bundle_root / "profiles"
    for prescribed_path in profiles_root.rglob("prescribed.yaml"):
        data = yaml.load(prescribed_path)
        if data is None:
            continue
        prescribed = validate_prescribed(data)

        # Filter by enabled profiles.
        profile = prescribed.id.split(".")[0]
        if profile not in state.profiles:
            continue

        # Skip already-overridden controls.
        if prescribed.id in state.overrides:
            continue

        # Skip controls whose applies_to doesn't match enabled profiles.
        # 'any' is always applicable; otherwise the profile must be in the list.
        if "any" not in prescribed.applies_to and profile not in prescribed.applies_to:
            continue

        domain = prescribed.id.split(".")[1]
        control_dir = prescribed_path.parent
        instruct_path = control_dir / "instruct.md"

        proposals.append(Proposal(
            control_id=prescribed.id,
            profile=profile,
            domain=domain,
            action_kind=ActionKind.MANUAL_ACTION,
            summary=prescribed.what.strip().splitlines()[0],
            instruct_path=instruct_path if instruct_path.exists() else None,
            depends_on=list(prescribed.depends_on),
        ))

    proposals.sort(key=lambda p: p.control_id)
    return proposals
```

- [ ] **Step 4: Run tests — PASS expected**

```bash
uv run pytest tests/test_setup_gap.py -v
uv run pytest -v
```

Expected: 6 new tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/setup/gap.py tests/test_setup_gap.py
git commit -m "feat: compute_proposals gap analysis"
git push
```

---

## Task 5: Batch + render proposals

**Files:**
- Create: `src/agent_weiss/lib/setup/batch.py`
- Create: `tests/test_setup_batch.py`

Group proposals by domain (one section per domain) and produce a numbered rendering for the user prompt. Numbering is global (1..N across all domains) so the user can refer to items by number directly.

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_setup_batch.py`:

```python
"""Tests for proposal batching + rendering."""
from pathlib import Path
from agent_weiss.lib.setup.types import Proposal, ActionKind
from agent_weiss.lib.setup.batch import batch_by_domain, render_proposals


def _proposal(cid: str, profile: str, domain: str, summary: str = "x") -> Proposal:
    return Proposal(
        control_id=cid,
        profile=profile,
        domain=domain,
        action_kind=ActionKind.MANUAL_ACTION,
        summary=summary,
    )


def test_batch_by_domain_groups_in_input_order():
    """Proposals are grouped by domain; domain key insertion order matches first-seen."""
    proposals = [
        _proposal("universal.docs.a", "universal", "docs"),
        _proposal("universal.security.b", "universal", "security"),
        _proposal("universal.docs.c", "universal", "docs"),
    ]
    batched = batch_by_domain(proposals)
    assert list(batched.keys()) == ["docs", "security"]
    assert len(batched["docs"]) == 2
    assert len(batched["security"]) == 1


def test_render_proposals_numbers_globally():
    """Numbers run 1..N across all domains in the rendered text."""
    proposals = [
        _proposal("universal.docs.a", "universal", "docs", "create AGENTS.md"),
        _proposal("universal.security.b", "universal", "security", "gitignore .env"),
        _proposal("universal.docs.c", "universal", "docs", "create CLAUDE.md"),
    ]
    text = render_proposals(proposals)
    assert "1." in text
    assert "2." in text
    assert "3." in text
    assert "create AGENTS.md" in text
    assert "create CLAUDE.md" in text
    # Domain headers present
    assert "docs" in text.lower()
    assert "security" in text.lower()


def test_render_proposals_groups_under_domain_headers():
    """The rendered text has a header per domain, with that domain's items
    listed under it before the next domain begins."""
    proposals = [
        _proposal("universal.docs.a", "universal", "docs", "create AGENTS.md"),
        _proposal("universal.security.b", "universal", "security", "gitignore .env"),
        _proposal("universal.docs.c", "universal", "docs", "create CLAUDE.md"),
    ]
    text = render_proposals(proposals)
    docs_pos = text.lower().index("docs")
    security_pos = text.lower().index("security")
    a_pos = text.index("create AGENTS.md")
    c_pos = text.index("create CLAUDE.md")
    b_pos = text.index("gitignore .env")
    assert docs_pos < a_pos < c_pos < security_pos < b_pos


def test_render_empty_proposals():
    """Empty list renders to a sensible message, not an error."""
    text = render_proposals([])
    assert text.strip()  # non-empty
```

- [ ] **Step 2: Run — FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_setup_batch.py -v
```

Expected: 4 tests fail on import.

- [ ] **Step 3: Implement batch.py**

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/setup/batch.py`:

```python
"""Group proposals by domain and render them as numbered prompt text.

Numbering is global (1..N) so the user can type "approve 3 5 7" without
caring about which domain each number belongs to.
"""
from __future__ import annotations
from collections import OrderedDict

from agent_weiss.lib.setup.types import Proposal


def batch_by_domain(proposals: list[Proposal]) -> dict[str, list[Proposal]]:
    """Group proposals by domain, preserving first-seen order of domains."""
    out: OrderedDict[str, list[Proposal]] = OrderedDict()
    for p in proposals:
        out.setdefault(p.domain, []).append(p)
    return dict(out)


def render_proposals(proposals: list[Proposal]) -> str:
    """Render proposals as numbered text, grouped by domain.

    Format:
        ## docs
        1. universal.docs.agents-md-present — Project has AGENTS.md ...
        2. universal.docs.claude-md-present — ...

        ## security
        3. universal.security.gitignore-secrets — ...

    Numbering is global (1..N) across all domains.
    """
    if not proposals:
        return "No setup proposals — every applicable control is satisfied or overridden."

    batched = batch_by_domain(proposals)
    lines: list[str] = []
    counter = 1
    for domain, items in batched.items():
        lines.append(f"## {domain}")
        for p in items:
            lines.append(f"{counter}. {p.control_id} — {p.summary}")
            counter += 1
        lines.append("")  # blank between domains
    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: Run — PASS**

```bash
uv run pytest -v
```

Expected: 4 new tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/setup/batch.py tests/test_setup_batch.py
git commit -m "feat: batch_by_domain + render_proposals"
git push
```

---

## Task 6: Verb parser

**Files:**
- Create: `src/agent_weiss/lib/setup/verbs.py`
- Create: `tests/test_setup_verbs.py`

Parse a free-form user input string into a `Decision`. Supported verbs:

- `approve all` → approve everything
- `approve <domain>` → approve all proposals in named domain (e.g., `approve docs`)
- `<numbers>` → approve the listed indices (e.g., `1 3 5` or `1,3,5`)
- `skip <numbers>` → skip the listed indices (with optional `: reason` after)
- `skip <numbers>: <reason>` → skip with override reason
- `explain <N>` → ask to explain item N (skill should re-prompt after)
- `dry-run` → write report and exit
- `cancel` → abort the loop

Parsing is forgiving on whitespace/case but strict on syntax.

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_setup_verbs.py`:

```python
"""Tests for verb parser."""
import pytest
from agent_weiss.lib.setup.verbs import parse_verb, VerbParseError


def test_approve_all():
    d = parse_verb("approve all", num_proposals=10, available_domains=["docs", "security"])
    assert d.approve_all is True
    assert d.approve_indices == []


def test_approve_all_case_insensitive():
    d = parse_verb("Approve All", num_proposals=10, available_domains=["docs"])
    assert d.approve_all is True


def test_approve_domain():
    d = parse_verb("approve docs", num_proposals=10, available_domains=["docs", "security"])
    assert d.approve_domains == ["docs"]
    assert d.approve_all is False


def test_approve_unknown_domain_raises():
    with pytest.raises(VerbParseError, match="domain"):
        parse_verb("approve other", num_proposals=10, available_domains=["docs"])


def test_approve_indices_space_separated():
    d = parse_verb("1 3 5", num_proposals=10, available_domains=["docs"])
    assert d.approve_indices == [1, 3, 5]


def test_approve_indices_comma_separated():
    d = parse_verb("1, 3, 5", num_proposals=10, available_domains=["docs"])
    assert d.approve_indices == [1, 3, 5]


def test_approve_index_out_of_range_raises():
    with pytest.raises(VerbParseError, match="range"):
        parse_verb("99", num_proposals=10, available_domains=["docs"])


def test_skip_indices():
    d = parse_verb("skip 2 4", num_proposals=10, available_domains=["docs"])
    assert d.skip_indices == [2, 4]


def test_skip_with_reason():
    d = parse_verb(
        "skip 2: we use mypy not ty",
        num_proposals=10,
        available_domains=["docs"],
    )
    assert d.skip_indices == [2]
    assert d.skip_reasons[2] == "we use mypy not ty"


def test_skip_multiple_with_reason_applies_to_all():
    d = parse_verb(
        "skip 2 3: legacy project",
        num_proposals=10,
        available_domains=["docs"],
    )
    assert d.skip_indices == [2, 3]
    assert d.skip_reasons[2] == "legacy project"
    assert d.skip_reasons[3] == "legacy project"


def test_explain():
    d = parse_verb("explain 4", num_proposals=10, available_domains=["docs"])
    assert d.explain_index == 4


def test_explain_out_of_range_raises():
    with pytest.raises(VerbParseError, match="range"):
        parse_verb("explain 99", num_proposals=10, available_domains=["docs"])


def test_dry_run():
    d = parse_verb("dry-run", num_proposals=10, available_domains=["docs"])
    assert d.dry_run is True


def test_cancel():
    d = parse_verb("cancel", num_proposals=10, available_domains=["docs"])
    assert d.cancel is True


def test_empty_input_raises():
    with pytest.raises(VerbParseError, match="empty"):
        parse_verb("   ", num_proposals=10, available_domains=["docs"])


def test_unknown_verb_raises():
    with pytest.raises(VerbParseError, match="unknown"):
        parse_verb("teleport 5", num_proposals=10, available_domains=["docs"])
```

- [ ] **Step 2: Run — FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_setup_verbs.py -v
```

Expected: 16 tests fail on import.

- [ ] **Step 3: Implement verbs.py**

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/setup/verbs.py`:

```python
"""Parse user-typed setup verbs into a Decision.

Grammar (case-insensitive on verb keywords):
    "approve all"              → approve_all=True
    "approve <domain>"         → approve_domains=[domain]
    "<numbers>"                → approve_indices=[...]
    "skip <numbers>[: reason]" → skip_indices=[...] (+ skip_reasons)
    "explain <N>"              → explain_index=N
    "dry-run"                  → dry_run=True
    "cancel"                   → cancel=True

Numbers may be space- or comma-separated. Indices are 1-based and validated
against num_proposals. Domain names validated against available_domains.
"""
from __future__ import annotations
import re

from agent_weiss.lib.setup.types import Decision


class VerbParseError(ValueError):
    """User-typed verb couldn't be parsed."""


_NUMBERS_RE = re.compile(r"[\s,]+")


def parse_verb(
    user_input: str,
    *,
    num_proposals: int,
    available_domains: list[str],
) -> Decision:
    """Parse user_input into a Decision. Raise VerbParseError on syntax issues."""
    text = user_input.strip()
    if not text:
        raise VerbParseError("empty input")

    lowered = text.lower()

    if lowered == "cancel":
        return Decision(cancel=True)
    if lowered == "dry-run":
        return Decision(dry_run=True)
    if lowered == "approve all":
        return Decision(approve_all=True)

    if lowered.startswith("approve "):
        rest = text[len("approve "):].strip()
        if rest.lower() not in [d.lower() for d in available_domains]:
            raise VerbParseError(
                f"unknown domain {rest!r} (available: {available_domains})"
            )
        # Match the original casing from available_domains
        canonical = next(d for d in available_domains if d.lower() == rest.lower())
        return Decision(approve_domains=[canonical])

    if lowered.startswith("explain "):
        rest = text[len("explain "):].strip()
        try:
            n = int(rest)
        except ValueError as e:
            raise VerbParseError(f"explain expects a number, got {rest!r}") from e
        if not (1 <= n <= num_proposals):
            raise VerbParseError(
                f"explain index {n} out of range (1..{num_proposals})"
            )
        return Decision(explain_index=n)

    if lowered.startswith("skip "):
        rest = text[len("skip "):].strip()
        nums_part, reason = _split_reason(rest)
        indices = _parse_numbers(nums_part, num_proposals)
        skip_reasons = {i: reason for i in indices} if reason else {}
        return Decision(skip_indices=indices, skip_reasons=skip_reasons)

    # Bare numbers (with optional commas) — approve those indices.
    if re.fullmatch(r"[0-9, ]+", text):
        indices = _parse_numbers(text, num_proposals)
        return Decision(approve_indices=indices)

    raise VerbParseError(f"unknown verb in {user_input!r}")


def _split_reason(text: str) -> tuple[str, str | None]:
    """Split 'numbers: reason' into ('numbers', 'reason') or ('numbers', None)."""
    if ":" in text:
        nums, reason = text.split(":", 1)
        return nums.strip(), reason.strip()
    return text, None


def _parse_numbers(text: str, num_proposals: int) -> list[int]:
    """Parse space- or comma-separated numbers; validate range."""
    text = text.strip()
    if not text:
        raise VerbParseError("expected one or more numbers")
    parts = [p for p in _NUMBERS_RE.split(text) if p]
    out: list[int] = []
    for p in parts:
        try:
            n = int(p)
        except ValueError as e:
            raise VerbParseError(f"not a number: {p!r}") from e
        if not (1 <= n <= num_proposals):
            raise VerbParseError(
                f"index {n} out of range (1..{num_proposals})"
            )
        out.append(n)
    return out
```

- [ ] **Step 4: Run — PASS**

```bash
uv run pytest tests/test_setup_verbs.py -v
uv run pytest -v
```

Expected: 16 new tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/setup/verbs.py tests/test_setup_verbs.py
git commit -m "feat: verb parser for setup approval UX"
git push
```

---

## Task 7: Backup writer

**Files:**
- Create: `src/agent_weiss/lib/setup/backup.py`
- Create: `tests/test_setup_backup.py`

Built now (foundation), even though Plan 3's MANUAL_ACTION path doesn't overwrite files. The future `INSTALL_FILE` and `MERGE_FRAGMENT` paths will use this.

Behavior: copy the existing file to `.agent-weiss/backups/<timestamp>/<relative_path>` before any overwrite. Returns the backup path. Idempotent — if no source file, returns None and is a no-op.

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_setup_backup.py`:

```python
"""Tests for backup writer."""
from pathlib import Path
import pytest

from agent_weiss.lib.setup.backup import backup_file


def test_backup_creates_timestamped_dir(tmp_path: Path):
    """Backup is written to .agent-weiss/backups/<timestamp>/<relative>."""
    target = tmp_path / "config.toml"
    target.write_text("original content\n")
    backup = backup_file(project_root=tmp_path, target=target, timestamp="2026-04-19T12-00-00")
    assert backup is not None
    assert backup == tmp_path / ".agent-weiss" / "backups" / "2026-04-19T12-00-00" / "config.toml"
    assert backup.exists()
    assert backup.read_text() == "original content\n"


def test_backup_preserves_relative_path(tmp_path: Path):
    """Nested target paths are preserved under the timestamp dir."""
    target = tmp_path / "nested" / "dir" / "file.txt"
    target.parent.mkdir(parents=True)
    target.write_text("nested content\n")
    backup = backup_file(project_root=tmp_path, target=target, timestamp="2026-04-19T12-00-00")
    assert backup == tmp_path / ".agent-weiss" / "backups" / "2026-04-19T12-00-00" / "nested" / "dir" / "file.txt"
    assert backup.read_text() == "nested content\n"


def test_backup_missing_source_returns_none(tmp_path: Path):
    """If target doesn't exist, no backup is written; return None."""
    target = tmp_path / "missing.txt"
    backup = backup_file(project_root=tmp_path, target=target, timestamp="2026-04-19T12-00-00")
    assert backup is None
    assert not (tmp_path / ".agent-weiss" / "backups").exists()


def test_backup_target_outside_project_raises(tmp_path: Path):
    """Refuse to back up files outside the project root."""
    elsewhere = tmp_path.parent / "elsewhere.txt"
    elsewhere.write_text("x")
    try:
        with pytest.raises(ValueError, match="outside project"):
            backup_file(project_root=tmp_path, target=elsewhere, timestamp="x")
    finally:
        elsewhere.unlink()
```

- [ ] **Step 2: Run — FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_setup_backup.py -v
```

Expected: 4 tests fail on import.

- [ ] **Step 3: Implement backup.py**

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/setup/backup.py`:

```python
"""Backup mechanism for setup writes.

Before any setup action overwrites a project file, the file is copied to
`.agent-weiss/backups/<timestamp>/<relative_path>`. Reversible by copying back.

Plan 3's MANUAL_ACTION path doesn't write files (so doesn't backup), but this
helper is built now so future INSTALL_FILE and MERGE_FRAGMENT paths can use it.
"""
from __future__ import annotations
import shutil
from pathlib import Path


BACKUPS_SUBDIR = ".agent-weiss/backups"


def backup_file(*, project_root: Path, target: Path, timestamp: str) -> Path | None:
    """Copy `target` into the backups dir, returning the backup path.

    Returns None if `target` doesn't exist (no-op).
    Raises ValueError if `target` is outside `project_root`.
    """
    if not target.exists():
        return None

    try:
        relative = target.resolve().relative_to(project_root.resolve())
    except ValueError as e:
        raise ValueError(
            f"target {target} is outside project {project_root}"
        ) from e

    backup_dir = project_root / BACKUPS_SUBDIR / timestamp
    backup_path = backup_dir / relative
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(target, backup_path)
    return backup_path
```

- [ ] **Step 4: Run — PASS**

```bash
uv run pytest tests/test_setup_backup.py -v
uv run pytest -v
```

Expected: 4 new pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/setup/backup.py tests/test_setup_backup.py
git commit -m "feat: backup_file writer (foundation for future install_file/merge_fragment paths)"
git push
```

---

## Task 8: `apply_proposal` — manual_action path

**Files:**
- Create: `src/agent_weiss/lib/setup/apply.py`
- Create: `tests/test_setup_apply.py`

For MANUAL_ACTION proposals, "applying" means recording the user's decision in state. There are three sub-cases:

- **Approved + confirmed handled** → no-op for state (the next verify run will check); we don't add an override. Returns the unchanged state.
- **Skipped without reason** → also no-op (treat as deferred). Returns unchanged state.
- **Skipped with reason** → record an `OverrideEntry` in `state.overrides[control_id]`.

Returns a new State (not mutating the input — keeps things easy to reason about).

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_setup_apply.py`:

```python
"""Tests for apply_proposal (manual_action path)."""
from pathlib import Path
from agent_weiss.lib.state import State
from agent_weiss.lib.setup.types import Proposal, ActionKind, OverrideEntry
from agent_weiss.lib.setup.apply import apply_proposal, ApplyOutcome


def _proposal(cid: str = "universal.docs.claude-md-present") -> Proposal:
    return Proposal(
        control_id=cid,
        profile=cid.split(".")[0],
        domain=cid.split(".")[1],
        action_kind=ActionKind.MANUAL_ACTION,
        summary="x",
    )


def test_apply_approved_is_noop_for_state():
    state = State(profiles=["universal"])
    p = _proposal()
    new_state, outcome = apply_proposal(
        proposal=p,
        state=state,
        outcome=ApplyOutcome.APPROVED,
        decided_at="2026-04-19",
    )
    assert outcome == ApplyOutcome.APPROVED
    assert new_state.overrides == {}


def test_apply_skipped_no_reason_is_noop():
    state = State(profiles=["universal"])
    p = _proposal()
    new_state, _ = apply_proposal(
        proposal=p,
        state=state,
        outcome=ApplyOutcome.SKIPPED,
        decided_at="2026-04-19",
    )
    assert new_state.overrides == {}


def test_apply_skipped_with_reason_records_override():
    state = State(profiles=["python"])
    p = _proposal("python.quality.ty-config")
    new_state, _ = apply_proposal(
        proposal=p,
        state=state,
        outcome=ApplyOutcome.SKIPPED,
        decided_at="2026-04-19",
        reason="we use mypy",
    )
    assert "python.quality.ty-config" in new_state.overrides
    assert new_state.overrides["python.quality.ty-config"].reason == "we use mypy"
    assert new_state.overrides["python.quality.ty-config"].decided_at == "2026-04-19"


def test_apply_does_not_mutate_input_state():
    state = State(profiles=["python"])
    p = _proposal("python.quality.ty-config")
    apply_proposal(
        proposal=p,
        state=state,
        outcome=ApplyOutcome.SKIPPED,
        decided_at="2026-04-19",
        reason="we use mypy",
    )
    assert state.overrides == {}  # original untouched


def test_apply_install_file_kind_raises_not_implemented():
    """Plan 3 doesn't implement INSTALL_FILE; calling it raises NotImplementedError."""
    import pytest
    p = Proposal(
        control_id="x.y.z",
        profile="x",
        domain="y",
        action_kind=ActionKind.INSTALL_FILE,
        summary="install x",
    )
    state = State(profiles=["x"])
    with pytest.raises(NotImplementedError, match="install_file"):
        apply_proposal(
            proposal=p,
            state=state,
            outcome=ApplyOutcome.APPROVED,
            decided_at="2026-04-19",
        )
```

- [ ] **Step 2: Run — FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_setup_apply.py -v
```

Expected: 5 tests fail on import.

- [ ] **Step 3: Implement apply.py**

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/setup/apply.py`:

```python
"""Apply a single proposal to state.

Plan 3 implements only ActionKind.MANUAL_ACTION:
- APPROVED: no state change (the next verify will check the project).
- SKIPPED without reason: no state change.
- SKIPPED with reason: record an OverrideEntry in state.overrides.

INSTALL_FILE and MERGE_FRAGMENT raise NotImplementedError until later plans
add the file-copy and config-merge logic.
"""
from __future__ import annotations
import copy
from dataclasses import replace
from enum import Enum

from agent_weiss.lib.state import State
from agent_weiss.lib.setup.types import Proposal, ActionKind, OverrideEntry


class ApplyOutcome(Enum):
    APPROVED = "approved"
    SKIPPED = "skipped"


def apply_proposal(
    *,
    proposal: Proposal,
    state: State,
    outcome: ApplyOutcome,
    decided_at: str,
    reason: str | None = None,
) -> tuple[State, ApplyOutcome]:
    """Apply a proposal to state. Returns (new_state, outcome).

    The input state is not mutated; a new State is returned with any overrides
    update applied.
    """
    if proposal.action_kind == ActionKind.INSTALL_FILE:
        raise NotImplementedError(
            "install_file action_kind is not implemented in Plan 3"
        )
    if proposal.action_kind == ActionKind.MERGE_FRAGMENT:
        raise NotImplementedError(
            "merge_fragment action_kind is not implemented in Plan 3"
        )

    # MANUAL_ACTION:
    if outcome == ApplyOutcome.APPROVED:
        return state, outcome
    if outcome == ApplyOutcome.SKIPPED and not reason:
        return state, outcome

    # SKIPPED with reason → record override.
    new_overrides = dict(state.overrides)
    new_overrides[proposal.control_id] = OverrideEntry(
        reason=reason or "",
        decided_at=decided_at,
    )
    new_state = replace(state, overrides=new_overrides, _raw=copy.deepcopy(state._raw))
    return new_state, outcome
```

- [ ] **Step 4: Run — PASS**

```bash
uv run pytest -v
```

Expected: 5 new pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/setup/apply.py tests/test_setup_apply.py
git commit -m "feat: apply_proposal (manual_action path; install_file/merge_fragment stubbed)"
git push
```

---

## Task 9: Dry-run report generator

**Files:**
- Create: `src/agent_weiss/lib/setup/dry_run.py`
- Create: `tests/test_setup_dry_run.py`

When the user types `dry-run`, write a markdown report listing what the setup phase would do, then exit. Report goes to `.agent-weiss/dry-run-<timestamp>.md`.

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_setup_dry_run.py`:

```python
"""Tests for dry-run report generator."""
from pathlib import Path
from agent_weiss.lib.setup.types import Proposal, ActionKind
from agent_weiss.lib.setup.dry_run import write_dry_run_report


def _proposal(cid: str, summary: str = "x") -> Proposal:
    return Proposal(
        control_id=cid,
        profile=cid.split(".")[0],
        domain=cid.split(".")[1],
        action_kind=ActionKind.MANUAL_ACTION,
        summary=summary,
    )


def test_write_dry_run_report_creates_file(tmp_path: Path):
    proposals = [
        _proposal("universal.docs.agents-md-present", "ensure AGENTS.md present"),
        _proposal("universal.security.gitignore-secrets", ".env in .gitignore"),
    ]
    path = write_dry_run_report(
        project_root=tmp_path,
        proposals=proposals,
        timestamp="2026-04-19T12-00-00",
    )
    assert path == tmp_path / ".agent-weiss" / "dry-run-2026-04-19T12-00-00.md"
    assert path.exists()


def test_dry_run_report_lists_all_proposals(tmp_path: Path):
    proposals = [
        _proposal("universal.docs.agents-md-present", "ensure AGENTS.md present"),
        _proposal("universal.security.gitignore-secrets", ".env in .gitignore"),
    ]
    path = write_dry_run_report(
        project_root=tmp_path,
        proposals=proposals,
        timestamp="2026-04-19T12-00-00",
    )
    text = path.read_text()
    assert "agents-md-present" in text
    assert "gitignore-secrets" in text
    assert "ensure AGENTS.md present" in text
    assert ".env in .gitignore" in text


def test_dry_run_report_groups_by_domain(tmp_path: Path):
    proposals = [
        _proposal("universal.docs.a", "x"),
        _proposal("universal.security.b", "y"),
        _proposal("universal.docs.c", "z"),
    ]
    path = write_dry_run_report(
        project_root=tmp_path,
        proposals=proposals,
        timestamp="2026-04-19T12-00-00",
    )
    text = path.read_text()
    docs_pos = text.lower().index("docs")
    security_pos = text.lower().index("security")
    assert docs_pos < security_pos


def test_dry_run_report_with_no_proposals(tmp_path: Path):
    path = write_dry_run_report(
        project_root=tmp_path,
        proposals=[],
        timestamp="2026-04-19T12-00-00",
    )
    assert path.exists()
    assert "no proposals" in path.read_text().lower() or "nothing to do" in path.read_text().lower()
```

- [ ] **Step 2: Run — FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_setup_dry_run.py -v
```

Expected: 4 fail on import.

- [ ] **Step 3: Implement dry_run.py**

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/setup/dry_run.py`:

```python
"""Generate a markdown report for `dry-run` mode.

The report lists every proposal grouped by domain so the user can review
without committing to any changes.
"""
from __future__ import annotations
from pathlib import Path

from agent_weiss.lib.setup.types import Proposal
from agent_weiss.lib.setup.batch import batch_by_domain


DRY_RUN_DIR = ".agent-weiss"


def write_dry_run_report(
    *,
    project_root: Path,
    proposals: list[Proposal],
    timestamp: str,
) -> Path:
    """Write the dry-run report and return its path."""
    report_dir = project_root / DRY_RUN_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"dry-run-{timestamp}.md"

    lines: list[str] = [f"# agent-weiss dry-run report ({timestamp})", ""]

    if not proposals:
        lines.append("No proposals — every applicable control is satisfied or overridden.")
        path.write_text("\n".join(lines) + "\n")
        return path

    lines.append(f"{len(proposals)} proposed action(s) across {len(set(p.domain for p in proposals))} domain(s).")
    lines.append("")

    batched = batch_by_domain(proposals)
    counter = 1
    for domain, items in batched.items():
        lines.append(f"## {domain}")
        lines.append("")
        for p in items:
            lines.append(f"### {counter}. {p.control_id}")
            lines.append("")
            lines.append(f"**Action:** {p.action_kind.value}")
            lines.append(f"**Summary:** {p.summary}")
            if p.depends_on:
                lines.append(f"**Depends on:** {', '.join(p.depends_on)}")
            if p.instruct_path is not None:
                lines.append(f"**Details:** see `{p.instruct_path.relative_to(project_root.parent) if p.instruct_path.is_relative_to(project_root.parent) else p.instruct_path.name}`")
            lines.append("")
            counter += 1

    path.write_text("\n".join(lines).rstrip() + "\n")
    return path
```

- [ ] **Step 4: Run — PASS**

```bash
uv run pytest -v
```

Expected: 4 new pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/setup/dry_run.py tests/test_setup_dry_run.py
git commit -m "feat: dry-run report generator"
git push
```

---

## Task 10: depends_on cascade resolver

**Files:**
- Create: `src/agent_weiss/lib/setup/cascade.py`
- Create: `tests/test_setup_cascade.py`

When a control X is declined and another control Y has `depends_on: [X]`, Y should be flagged for re-decision (probably auto-skipped). This task implements the resolver that, given a Decision over a list of proposals, returns an updated Decision with cascaded skips.

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_setup_cascade.py`:

```python
"""Tests for depends_on cascade."""
from agent_weiss.lib.setup.types import Proposal, ActionKind, Decision
from agent_weiss.lib.setup.cascade import cascade_skips


def _proposal(cid: str, depends_on: list[str] | None = None) -> Proposal:
    return Proposal(
        control_id=cid,
        profile=cid.split(".")[0],
        domain=cid.split(".")[1],
        action_kind=ActionKind.MANUAL_ACTION,
        summary="x",
        depends_on=depends_on or [],
    )


def test_no_dependencies_no_cascade():
    """If no proposal has depends_on, decision is unchanged."""
    proposals = [_proposal("a.b.c"), _proposal("a.b.d")]
    decision = Decision(approve_indices=[1], skip_indices=[2])
    result = cascade_skips(proposals=proposals, decision=decision)
    assert result.approve_indices == [1]
    assert result.skip_indices == [2]


def test_cascade_skips_dependent_when_dependency_skipped():
    """If Y depends on X and X is skipped, Y is auto-skipped with cascade reason."""
    proposals = [
        _proposal("a.b.x"),
        _proposal("a.b.y", depends_on=["a.b.x"]),
        _proposal("a.b.z"),
    ]
    # User skips index 1 (a.b.x); index 2 (a.b.y) should also be skipped.
    decision = Decision(skip_indices=[1], approve_indices=[3])
    result = cascade_skips(proposals=proposals, decision=decision)
    assert 2 in result.skip_indices
    assert 2 in result.skip_reasons
    assert "a.b.x" in result.skip_reasons[2].lower()


def test_cascade_does_not_remove_explicit_approval():
    """If user explicitly approved Y but X is skipped, Y still gets cascade-skipped (override safety)."""
    proposals = [
        _proposal("a.b.x"),
        _proposal("a.b.y", depends_on=["a.b.x"]),
    ]
    decision = Decision(skip_indices=[1], approve_indices=[2])
    result = cascade_skips(proposals=proposals, decision=decision)
    # Y moved from approve to skip
    assert 2 not in result.approve_indices
    assert 2 in result.skip_indices


def test_cascade_does_not_affect_already_skipped():
    """Already-skipped items stay skipped; their existing reasons are preserved."""
    proposals = [
        _proposal("a.b.x"),
        _proposal("a.b.y", depends_on=["a.b.x"]),
    ]
    decision = Decision(
        skip_indices=[1, 2],
        skip_reasons={2: "user reason"},
    )
    result = cascade_skips(proposals=proposals, decision=decision)
    assert result.skip_reasons[2] == "user reason"


def test_transitive_cascade():
    """If A→B→C and A is skipped, both B and C are cascaded."""
    proposals = [
        _proposal("a.b.A"),
        _proposal("a.b.B", depends_on=["a.b.A"]),
        _proposal("a.b.C", depends_on=["a.b.B"]),
    ]
    decision = Decision(skip_indices=[1], approve_indices=[2, 3])
    result = cascade_skips(proposals=proposals, decision=decision)
    assert 2 in result.skip_indices
    assert 3 in result.skip_indices
```

- [ ] **Step 2: Run — FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_setup_cascade.py -v
```

Expected: 5 fail on import.

- [ ] **Step 3: Implement cascade.py**

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/setup/cascade.py`:

```python
"""depends_on cascade: when a control's dependency is skipped, skip it too.

Iterative algorithm:
1. Build set of skipped control_ids from decision.skip_indices.
2. For each proposal, if any of its depends_on is skipped, mark it skipped
   too (with a synthesized reason).
3. Repeat until no new skips.

Then re-render the Decision.
"""
from __future__ import annotations
from dataclasses import replace

from agent_weiss.lib.setup.types import Proposal, Decision


def cascade_skips(
    *,
    proposals: list[Proposal],
    decision: Decision,
) -> Decision:
    """Return a new Decision with cascaded skips applied.

    Approve_indices that depend on a skipped control are moved to skip_indices
    with a synthesized reason like "cascaded skip — depends on X (skipped)".
    """
    # 1-based index → control_id
    by_index = {i + 1: p for i, p in enumerate(proposals)}
    by_id = {p.control_id: i + 1 for i, p in enumerate(proposals)}

    skip_indices = list(decision.skip_indices)
    skip_reasons = dict(decision.skip_reasons)
    approve_indices = list(decision.approve_indices)

    skipped_ids = {by_index[i].control_id for i in skip_indices if i in by_index}

    changed = True
    while changed:
        changed = False
        for i, p in by_index.items():
            if i in skip_indices:
                continue
            for dep in p.depends_on:
                if dep in skipped_ids:
                    skip_indices.append(i)
                    skip_reasons[i] = f"cascaded skip — depends on {dep} (skipped)"
                    if i in approve_indices:
                        approve_indices.remove(i)
                    skipped_ids.add(p.control_id)
                    changed = True
                    break

    return replace(
        decision,
        approve_indices=sorted(set(approve_indices)),
        skip_indices=sorted(set(skip_indices)),
        skip_reasons=skip_reasons,
    )
```

- [ ] **Step 4: Run — PASS**

```bash
uv run pytest -v
```

Expected: 5 new pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/setup/cascade.py tests/test_setup_cascade.py
git commit -m "feat: depends_on cascade resolver"
git push
```

---

## Task 11: Reconcile prompt batching

**Files:**
- Modify: `src/agent_weiss/lib/reconcile.py` (add `render_anomalies` function)
- Create: `tests/test_reconcile_render.py`

The Reconcile UX should use the same batching pattern as Setup (per roadmap §Approval UX). Plan 1's `reconcile()` returns a typed `ReconcileReport`; Plan 3 adds `render_anomalies()` that produces a numbered list grouped by anomaly kind, suitable for the same kind of user-prompt loop.

The verb parser already handles numbers; the skill can reuse it. Just need rendering.

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_reconcile_render.py`:

```python
"""Tests for reconcile rendering (batching pattern matches setup)."""
from agent_weiss.lib.reconcile import Anomaly, ReconcileReport, render_anomalies


def test_render_empty_report():
    text = render_anomalies(ReconcileReport())
    assert text.strip()  # non-empty
    assert "no anomalies" in text.lower() or "nothing" in text.lower()


def test_render_groups_by_kind():
    report = ReconcileReport(anomalies=[
        Anomaly(kind="orphan", path=".agent-weiss/policies/a.rego", detail="x"),
        Anomaly(kind="ghost", path=".agent-weiss/policies/b.rego", detail="y"),
        Anomaly(kind="orphan", path=".agent-weiss/policies/c.rego", detail="z"),
    ])
    text = render_anomalies(report)
    orphan_pos = text.lower().index("orphan")
    ghost_pos = text.lower().index("ghost")
    a_pos = text.index("a.rego")
    b_pos = text.index("b.rego")
    c_pos = text.index("c.rego")
    # orphans are listed before ghosts by stable iteration order
    assert orphan_pos < ghost_pos
    # both orphans are under the orphan header
    assert a_pos < ghost_pos
    assert c_pos < ghost_pos


def test_render_numbers_globally():
    report = ReconcileReport(anomalies=[
        Anomaly(kind="orphan", path="a", detail="x"),
        Anomaly(kind="ghost", path="b", detail="y"),
        Anomaly(kind="locally_modified", path="c", detail="z"),
    ])
    text = render_anomalies(report)
    assert "1." in text
    assert "2." in text
    assert "3." in text
```

- [ ] **Step 2: Run — FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_reconcile_render.py -v
```

Expected: 3 fail on import.

- [ ] **Step 3: Add render_anomalies to reconcile.py**

Append to `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/reconcile.py`:

```python


def render_anomalies(report: ReconcileReport) -> str:
    """Render anomalies as numbered text, grouped by anomaly kind.

    Mirrors the setup render_proposals shape so the skill can reuse the same
    user-prompt verbs (numbers / `skip` / `cancel` etc.).
    """
    if not report.anomalies:
        return "No anomalies — state and disk agree.\n"

    # Group by kind preserving first-seen order.
    grouped: dict[str, list[Anomaly]] = {}
    for a in report.anomalies:
        grouped.setdefault(a.kind, []).append(a)

    lines: list[str] = []
    counter = 1
    for kind, items in grouped.items():
        lines.append(f"## {kind}")
        for a in items:
            lines.append(f"{counter}. {a.path} — {a.detail}")
            counter += 1
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: Run — PASS**

```bash
uv run pytest -v
```

Expected: 3 new pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/reconcile.py tests/test_reconcile_render.py
git commit -m "feat: render_anomalies — reconcile UX uses same batching as setup"
git push
```

---

## Task 12: Update skill.md with the setup loop

**Files:**
- Modify: `.claude/skills/agent-weiss/SKILL.md`

Plan 1's skill.md sketches the loop in pseudocode. Plan 3 turns the Setup phase section into actually-runnable instructions: which Python helpers to call, in what order, with what user-input parsing. The Reconcile section gets the same treatment.

- [ ] **Step 1: Read current skill.md**

```bash
cat /Users/iorlas/Workspaces/agent-weiss/.claude/skills/agent-weiss/SKILL.md
```

Verify the current shape: frontmatter + sections (Bundle root, Standard run loop with 7 numbered steps, What you must NEVER do, Cross-references).

- [ ] **Step 2: Replace section 2 (Reconcile) and section 4 (Setup phase)**

In `/Users/iorlas/Workspaces/agent-weiss/.claude/skills/agent-weiss/SKILL.md`, replace the entire `### 2. Reconcile` section content (between `### 2. Reconcile` and `### 3. Confirm profiles`) with:

```markdown
### 2. Reconcile

Detect drift between `.agent-weiss.yaml` state and the project's working tree.
The reconciliation detector is non-destructive — it only reports anomalies.

```python
from pathlib import Path
from agent_weiss.lib.reconcile import reconcile, render_anomalies

report = reconcile(Path("<project_root>"))
print(render_anomalies(report))
```

If `report.anomalies` is non-empty, prompt the user with the rendered text
followed by:

> "Resolve these anomalies — verbs: `<numbers>` to mark resolved, `skip <numbers>: <reason>` to override, `cancel`. Or describe a different action you'd like me to take."

Parse user input with `agent_weiss.lib.setup.verbs.parse_verb` (same parser
as the Setup phase). Apply per-anomaly resolutions to state — for orphans,
either re-track them in `prescribed_files` or delete them; for ghosts, either
restore from bundle or remove from `prescribed_files`; for locally_modified,
either accept the local version (re-hash) or restore from bundle.

> Plan 3 limitation: Reconciliation is detection + rendering. Per-anomaly
> apply logic (re-track / restore / accept) is handled by you, the skill —
> follow the user's choice and write the resulting state via `write_state`.
```

Then replace the entire `### 4. Setup phase` section content (between `### 4. Setup phase` and `### 5. Verify phase`) with:

```markdown
### 4. Setup phase

Compute proposals, batch by domain, render to the user, parse their verb,
cascade dependencies, and apply.

```python
from pathlib import Path
from datetime import datetime
from agent_weiss.lib.state import read_state, write_state
from agent_weiss.lib.bundle import resolve_bundle_root
from agent_weiss.lib.setup.gap import compute_proposals
from agent_weiss.lib.setup.batch import render_proposals
from agent_weiss.lib.setup.verbs import parse_verb, VerbParseError
from agent_weiss.lib.setup.cascade import cascade_skips
from agent_weiss.lib.setup.apply import apply_proposal, ApplyOutcome
from agent_weiss.lib.setup.dry_run import write_dry_run_report

project_root = Path("<project_root>")
state = read_state(project_root)
bundle = resolve_bundle_root()

proposals = compute_proposals(
    project_root=project_root,
    bundle_root=bundle,
    state=state,
)
prompt_text = render_proposals(proposals)
domains = sorted({p.domain for p in proposals})
```

Show `prompt_text` to the user. Then prompt:

> "Which to approve? Verbs: `approve all`, `approve <domain>`, `<numbers>`,
> `skip <numbers>[: reason]`, `explain <N>`, `dry-run`, `cancel`."

Loop:

```python
while True:
    user_input = read_user_input()  # the skill — your job
    try:
        decision = parse_verb(
            user_input,
            num_proposals=len(proposals),
            available_domains=domains,
        )
    except VerbParseError as e:
        show_error_and_reprompt(e)
        continue

    if decision.cancel:
        return  # abort the loop

    if decision.dry_run:
        ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        report_path = write_dry_run_report(
            project_root=project_root,
            proposals=proposals,
            timestamp=ts,
        )
        print(f"Dry-run report written to {report_path}. Exiting.")
        return

    if decision.explain_index is not None:
        show_instruct_md(proposals[decision.explain_index - 1])
        continue  # re-prompt

    break

# Cascade skips for declined dependencies
decision = cascade_skips(proposals=proposals, decision=decision)

# Apply each proposal's outcome.
decided_at = datetime.now().date().isoformat()
for i, p in enumerate(proposals, start=1):
    if decision.approve_all or i in decision.approve_indices or p.domain in decision.approve_domains:
        outcome = ApplyOutcome.APPROVED
        reason = None
    elif i in decision.skip_indices:
        outcome = ApplyOutcome.SKIPPED
        reason = decision.skip_reasons.get(i)
    else:
        # Neither approved nor skipped — treat as deferred (no state change).
        continue

    state, _ = apply_proposal(
        proposal=p,
        state=state,
        outcome=outcome,
        decided_at=decided_at,
        reason=reason,
    )

write_state(project_root, state)
```

For each MANUAL_ACTION proposal that was approved, you (the skill) must show
the user the contents of `proposal.instruct_path` so they can carry out the
action manually. Confirm with them ("done?") before recording approval.

For approved proposals where the user confirmed handled, the next Verify run
(step 5) checks that the action stuck. For declined proposals with a reason,
the override is recorded and counts as 'pass' in the Setup score (Plan 4).

> Plan 3 limitation: only MANUAL_ACTION proposals are supported. INSTALL_FILE
> and MERGE_FRAGMENT raise NotImplementedError until later plans add file
> install + config-merge logic.
```

- [ ] **Step 3: Verify pytest still passes**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest -v
```

Expected: same count as before this task (no test changes).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/agent-weiss/SKILL.md
git commit -m "docs: skill.md setup + reconcile loop wiring"
git push
```

---

## Task 13: Roadmap update + tag milestone

**Files:**
- Modify: `/Users/iorlas/Workspaces/agent-harness/docs/superpowers/plans/2026-04-14-agent-weiss-roadmap.md`

- [ ] **Step 1: Update roadmap status**

Edit the roadmap. Change Plan 3's `Status` from `Pending` to `Done`.

```bash
cd /Users/iorlas/Workspaces/agent-harness
git add docs/superpowers/plans/2026-04-14-agent-weiss-roadmap.md
git commit -m "roadmap: mark agent-weiss Plan 3 (Setup Workflow & Approval UX) complete"
git push
```

- [ ] **Step 2: Tag the milestone**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
git tag -a setup-workflow -m "Plan 3 complete: setup orchestration primitives + skill wiring"
git push origin setup-workflow
```

- [ ] **Step 3: Final sanity check**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest -v
gh run list --repo yoselabs/agent-weiss --limit 1  # confirm CI green
git tag --list | grep -E '(foundations|control|setup)'
```

Expected:
- All tests pass (~170+, depending on exact count)
- Latest CI run = `success`
- Tags listed: `foundations-mvp`, `control-library`, `setup-workflow`

---

## Plan-completion checklist

Before declaring Plan 3 done:
- [ ] All 13 tasks committed and pushed
- [ ] CI green on `main`
- [ ] `uv run pytest -v` passes locally
- [ ] All Rego policy tests still pass (`conftest verify` on each policy dir)
- [ ] Roadmap updated in agent-harness repo: Plan 3 → Done
- [ ] Tag `setup-workflow` pushed
- [ ] No TODO / TBD / "fix later" markers in new code
- [ ] skill.md no longer references the OLD setup-phase pseudocode

## After Plan 3 completes

The natural next step is **Plan 4: Verify Workflow & Scoring** — runs each control's check.sh, parses the JSON contract output, computes the two scores per spec §7, generates the human-readable report.

Plan 4 will likely also revisit ActionKind to determine whether the gap analysis should be driven by check.sh results (failing or setup-unmet → propose) rather than the conservative "every applicable control" approach of Plan 3. That's a v1 refinement, not a redesign — the orchestration layer Plan 3 ships stays.

If `INSTALL_FILE` or `MERGE_FRAGMENT` action kinds are needed before Plan 5 ships, write a small Plan 3.5 to add them — the data types are already in place, only the apply.py branch is stubbed.
