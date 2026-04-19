# agent-weiss Verify Workflow & Scoring (Plan 4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run every applicable control's `check.sh`, collect results, compute Setup + Quality scores per spec §7, format the human-readable report. Wire these into `skill.md` after the Setup phase Plan 3 already wired in.

**Architecture:** New `src/agent_weiss/lib/verify/` package. Each module is small + testable: results, dispatcher (subprocess invocation), scoring (two formulas), formatter (markdown report). Skill.md uses them at sections 5 (Verify) and 6 (Score and report).

**Tech Stack:** existing (Python 3.12+, pytest, ruamel.yaml, conftest for Rego). No new deps.

**Repository:** `/Users/iorlas/Workspaces/agent-weiss` (Plan 3 complete; tagged `setup-workflow` at commit `1b1042e`, 201 tests).

**Spec / roadmap:**
- `docs/superpowers/specs/2026-04-14-agent-weiss-design.md` (esp. §3 contract, §7 scores)
- `docs/superpowers/plans/2026-04-14-agent-weiss-roadmap.md` (cross-cutting decisions live here)
- Prior plans: foundations / control-library / setup-workflow

**Plan scope (in):**
- `ControlResult` dataclass (extends Plan 1's `CheckResult` with profile + domain + control_id)
- Verify dispatcher: walk applicable controls, run each `check.sh` with proper env + cwd, parse contract output, build `ControlResult`s
- Setup score: per-control 100 if (pass | fail | overridden) else 0; per-domain avg; total avg of domains
- Quality score: per-control 100 if pass / 0 if fail / EXCLUDED if setup-unmet; per-domain avg of measurable; total avg
- Report formatter: combined markdown with per-domain breakdown + per-control checkmarks + overall scores
- skill.md updates: Verify phase + Score phase + Report phase made concrete

**Plan scope (out — handled later):**
- Verify-driven proposals (currently Plan 3's `compute_proposals` returns every applicable control; could be refined post-verify to only return failing/setup-unmet ones — defer to a Plan 4.5 if the conservative output proves noisy)
- Persisting scores into `.agent-weiss.yaml` (per roadmap §Workflow: "Re-evaluated each run, never cached." — confirmed: scores stay transient)
- Distribution packaging (Plan 5)
- Drift refresh UX (Plan 6)
- Concurrent control execution (sequential is fine for v1; the Plan 3 review flagged the rego.py data-file race but that only matters for parallel runs)

---

## Scoring formula reference (from spec §7)

**Setup score** — measures whether the infrastructure each control needs is in place.

- Per control:
  - `100` if status is `pass` OR `fail` (the check ran, infrastructure works)
  - `100` if the control is in `state.overrides` (override-with-reason counts as pass)
  - `0` if status is `setup-unmet` (infrastructure missing — that's a setup failure)
- Per domain: arithmetic mean of per-control scores in that domain
- Total: arithmetic mean of per-domain scores

**Quality score** — measures whether the controls themselves pass.

- Per control:
  - `100` if status is `pass`
  - `0` if status is `fail`
  - **EXCLUDED** if status is `setup-unmet` (don't penalize quality for missing infra)
  - Overrides contribute `100` (an override is a deliberate "this control's outcome is the user's call, treat as pass")
- Per domain: arithmetic mean of measurable per-control scores; if no measurable controls, the domain is excluded from the total
- Total: arithmetic mean of per-domain scores (excluded domains excluded)

Both scores rounded to nearest integer for display, but stored as float.

---

## Pause points

- **After Task 2:** results + dispatcher shipped — verify works end-to-end via Python (no UX yet).
- **After Task 4:** both scoring formulas done; report formatter remains.
- **After Task 6:** Plan 4 complete, tagged.

---

## Task 1: ControlResult type + verify package skeleton

**Files:**
- Create: `src/agent_weiss/lib/verify/__init__.py`
- Create: `src/agent_weiss/lib/verify/types.py`
- Create: `tests/test_verify_types.py`

Establish the `verify/` package with the `ControlResult` dataclass that downstream tasks (dispatcher, scoring, formatter) all use.

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_verify_types.py`:

```python
"""Tests for verify result types."""
import pytest
from agent_weiss.lib.contract import Status
from agent_weiss.lib.verify.types import ControlResult


def test_control_result_minimum_fields():
    r = ControlResult(
        control_id="universal.docs.agents-md-present",
        profile="universal",
        domain="docs",
        status=Status.PASS,
        summary="AGENTS.md present",
        findings_count=0,
    )
    assert r.control_id == "universal.docs.agents-md-present"
    assert r.profile == "universal"
    assert r.domain == "docs"
    assert r.status is Status.PASS
    assert r.findings_count == 0


def test_control_result_optional_fields():
    r = ControlResult(
        control_id="x.y.z",
        profile="x",
        domain="y",
        status=Status.SETUP_UNMET,
        summary="conftest not found",
        findings_count=0,
        install="brew install conftest",
        details_path=None,
    )
    assert r.install == "brew install conftest"
    assert r.details_path is None


def test_control_result_is_frozen():
    r = ControlResult(
        control_id="a.b.c",
        profile="a",
        domain="b",
        status=Status.FAIL,
        summary="bad",
        findings_count=3,
    )
    with pytest.raises((AttributeError, TypeError)):
        r.summary = "mutated"
```

- [ ] **Step 2: Run — verify FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_verify_types.py -v
```

Expected: 3 tests fail on import.

- [ ] **Step 3: Implement the package**

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/verify/__init__.py`:

```python
"""Verify workflow: run check.sh per control, parse results, score, format.

The skill.md Verify and Score phases call these helpers in sequence:
1. run_all_checks → list[ControlResult]
2. compute_setup_score / compute_quality_score → ScoreReport
3. format_report → markdown string for the user
"""
```

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/verify/types.py`:

```python
"""Verify result types."""
from __future__ import annotations
from dataclasses import dataclass

from agent_weiss.lib.contract import Status


@dataclass(frozen=True)
class ControlResult:
    """Outcome of running one control's check.sh.

    Composed from the control's identifying triple (id, profile, domain) plus
    the parsed check.sh output (status, summary, findings_count, install,
    details_path). One ControlResult per control per verify run.
    """
    control_id: str
    profile: str
    domain: str
    status: Status
    summary: str
    findings_count: int = 0
    install: str | None = None
    details_path: str | None = None
```

- [ ] **Step 4: Run — PASS**

```bash
uv run pytest -v
```

Expected: 3 new pass; total 204 (201 + 3).

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/verify/ tests/test_verify_types.py
git commit -m "feat: ControlResult type + verify package skeleton"
git push
```

---

## Task 2: Verify dispatcher — `run_all_checks`

**Files:**
- Create: `src/agent_weiss/lib/verify/dispatch.py`
- Create: `tests/test_verify_dispatch.py`

Walk the bundle's profiles tree, match against `state.profiles`, run each applicable control's `check.sh` against the project, parse output via Plan 1's `parse_check_output`, build a `ControlResult`. Collect all results.

The fixture runner from Plan 1 already invokes check.sh files this way (per-control); this task generalizes it for the actual user loop.

**Timeout:** each `check.sh` runs under a per-control subprocess timeout (default 30s). A hanging check yields a `setup-unmet` ControlResult with a "timed out" summary rather than blocking the entire verify pass.

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_verify_dispatch.py`:

```python
"""Tests for verify dispatcher."""
from pathlib import Path
import pytest

from agent_weiss.lib.contract import Status
from agent_weiss.lib.verify.dispatch import run_all_checks
from agent_weiss.lib.state import State


REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE = REPO_ROOT


def test_run_all_checks_against_pass_fixture(tmp_path: Path):
    """Run universal controls against a fixture project containing all required files."""
    # Build a project that satisfies all 8 universal controls.
    (tmp_path / "AGENTS.md").write_text("# agent instructions\n")
    (tmp_path / "CLAUDE.md").write_text("# claude instructions\n")
    (tmp_path / "README.md").write_text("# project\n")
    (tmp_path / ".gitignore").write_text(".env\n.env.*\n")
    (tmp_path / "LICENSE").write_text("MIT\n")
    (tmp_path / ".pre-commit-config.yaml").write_text("repos:\n  - repo: https://github.com/gitleaks/gitleaks\n    hooks:\n      - id: gitleaks\n")
    # No .env files in tree — env-files-not-tracked passes.

    state = State(profiles=["universal"])
    results = run_all_checks(
        project_root=tmp_path,
        bundle_root=BUNDLE,
        state=state,
    )

    assert len(results) == 8
    by_id = {r.control_id: r for r in results}

    # Pure shell controls should all pass.
    assert by_id["universal.docs.agents-md-present"].status is Status.PASS
    assert by_id["universal.docs.claude-md-present"].status is Status.PASS
    assert by_id["universal.docs.readme-present"].status is Status.PASS
    assert by_id["universal.security.env-files-not-tracked"].status is Status.PASS
    assert by_id["universal.security.gitleaks-precommit"].status is Status.PASS
    assert by_id["universal.vcs.gitignore-present"].status is Status.PASS
    assert by_id["universal.vcs.license-present"].status is Status.PASS

    # gitignore-secrets is a Rego control — passes if conftest is installed
    # AND .gitignore has both .env and .env.*. Status should be pass or setup-unmet
    # depending on whether conftest is available.
    assert by_id["universal.security.gitignore-secrets"].status in (Status.PASS, Status.SETUP_UNMET)


def test_run_all_checks_against_empty_fixture(tmp_path: Path):
    """Run against an empty project — most controls fail, none crash."""
    state = State(profiles=["universal"])
    results = run_all_checks(
        project_root=tmp_path,
        bundle_root=BUNDLE,
        state=state,
    )
    assert len(results) == 8
    # Every result has a parsed status (no exceptions).
    for r in results:
        assert r.status in (Status.PASS, Status.FAIL, Status.SETUP_UNMET)


def test_run_all_checks_filters_by_state_profiles(tmp_path: Path):
    """profiles=['python'] runs only the 5 python controls."""
    state = State(profiles=["python"])
    results = run_all_checks(
        project_root=tmp_path,
        bundle_root=BUNDLE,
        state=state,
    )
    assert len(results) == 5
    assert {r.profile for r in results} == {"python"}


def test_run_all_checks_sets_profile_and_domain(tmp_path: Path):
    """Each result carries profile + domain derived from the control id."""
    state = State(profiles=["universal"])
    results = run_all_checks(
        project_root=tmp_path,
        bundle_root=BUNDLE,
        state=state,
    )
    for r in results:
        parts = r.control_id.split(".")
        assert r.profile == parts[0]
        assert r.domain == parts[1]


def test_run_all_checks_handles_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A check.sh that exceeds the timeout yields setup-unmet, not an exception."""
    import subprocess as _sp

    real_run = _sp.run

    def fake_run(*args, **kwargs):
        # Any invocation of check.sh under the timeout raises TimeoutExpired.
        if args and isinstance(args[0], list) and args[0][:1] == ["sh"]:
            raise _sp.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 0))
        return real_run(*args, **kwargs)

    monkeypatch.setattr("agent_weiss.lib.verify.dispatch.subprocess.run", fake_run)

    state = State(profiles=["universal"])
    results = run_all_checks(
        project_root=tmp_path,
        bundle_root=BUNDLE,
        state=state,
        timeout=0.01,
    )
    assert len(results) == 8
    for r in results:
        assert r.status is Status.SETUP_UNMET
        assert "timed out" in r.summary.lower()
```

- [ ] **Step 2: Run — verify FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_verify_dispatch.py -v
```

Expected: 5 tests fail on import.

- [ ] **Step 3: Implement dispatch.py**

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/verify/dispatch.py`:

```python
"""Run every applicable control's check.sh; collect ControlResults.

For each control in the bundle whose profile matches state.profiles AND whose
applies_to allows it, invoke check.sh with cwd=project_root and env including
AGENT_WEISS_BUNDLE pointing at bundle_root. Parse the output via the contract
parser, build a ControlResult, append to the list.

Each check.sh runs under a per-control subprocess timeout (default 30s). A
timeout or contract violation yields a setup-unmet ControlResult so the verify
pass doesn't crash on one bad control.
"""
from __future__ import annotations
import os
import subprocess
from pathlib import Path

from ruamel.yaml import YAML

from agent_weiss.lib.state import State
from agent_weiss.lib.schemas import validate_prescribed
from agent_weiss.lib.contract import (
    Status,
    parse_check_output,
    ContractError,
)
from agent_weiss.lib.verify.types import ControlResult


DEFAULT_CHECK_TIMEOUT_SECONDS = 30.0


def run_all_checks(
    *,
    project_root: Path,
    bundle_root: Path,
    state: State,
    timeout: float = DEFAULT_CHECK_TIMEOUT_SECONDS,
) -> list[ControlResult]:
    """Run every applicable control's check.sh; return ControlResults sorted by id."""
    yaml = YAML(typ="safe")
    results: list[ControlResult] = []

    profiles_root = bundle_root / "profiles"
    for prescribed_path in profiles_root.rglob("prescribed.yaml"):
        data = yaml.load(prescribed_path)
        if data is None:
            continue
        prescribed = validate_prescribed(data)

        profile = prescribed.id.split(".")[0]
        domain = prescribed.id.split(".")[1]

        # Filter by enabled profiles.
        if profile not in state.profiles:
            continue

        # Filter by applies_to: 'any' OR matches profile.
        if "any" not in prescribed.applies_to and profile not in prescribed.applies_to:
            continue

        check_sh = prescribed_path.parent / "check.sh"
        if not check_sh.exists():
            results.append(ControlResult(
                control_id=prescribed.id,
                profile=profile,
                domain=domain,
                status=Status.SETUP_UNMET,
                summary=f"check.sh missing at {check_sh}",
            ))
            continue

        env = {**os.environ, "AGENT_WEISS_BUNDLE": str(bundle_root)}
        try:
            proc = subprocess.run(
                ["sh", str(check_sh)],
                cwd=project_root,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            results.append(ControlResult(
                control_id=prescribed.id,
                profile=profile,
                domain=domain,
                status=Status.SETUP_UNMET,
                summary=f"check.sh timed out after {timeout}s",
            ))
            continue

        try:
            parsed = parse_check_output(stdout=proc.stdout, exit_code=proc.returncode)
        except ContractError as e:
            results.append(ControlResult(
                control_id=prescribed.id,
                profile=profile,
                domain=domain,
                status=Status.SETUP_UNMET,
                summary=f"contract violation: {e}",
            ))
            continue

        results.append(ControlResult(
            control_id=prescribed.id,
            profile=profile,
            domain=domain,
            status=parsed.status,
            summary=parsed.summary,
            findings_count=parsed.findings_count,
            install=parsed.install,
            details_path=parsed.details_path,
        ))

    results.sort(key=lambda r: r.control_id)
    return results
```

- [ ] **Step 4: Run — verify PASS**

```bash
uv run pytest tests/test_verify_dispatch.py -v
uv run pytest -v
```

Expected: 5 new pass; total 209.

If `test_run_all_checks_against_pass_fixture` reports unexpected fails for non-Rego controls (i.e., shell controls that should pass against the fixture), debug. The fixture is constructed to satisfy each control's check.sh; if a check returns fail, either the fixture is missing a file or the check has a bug.

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/verify/dispatch.py tests/test_verify_dispatch.py
git commit -m "feat: verify dispatcher (run_all_checks)"
git push
```

---

## Task 3: Setup score

**Files:**
- Create: `src/agent_weiss/lib/verify/score.py`
- Create: `tests/test_verify_score_setup.py`

Implements the Setup score per spec §7. The same module will hold the Quality score in Task 4.

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_verify_score_setup.py`:

```python
"""Tests for setup scoring."""
from agent_weiss.lib.contract import Status
from agent_weiss.lib.verify.types import ControlResult
from agent_weiss.lib.verify.score import compute_setup_score, ScoreReport
from agent_weiss.lib.setup.types import OverrideEntry


def _result(cid: str, status: Status) -> ControlResult:
    return ControlResult(
        control_id=cid,
        profile=cid.split(".")[0],
        domain=cid.split(".")[1],
        status=status,
        summary="x",
    )


def test_setup_score_pass_is_100():
    results = [_result("a.b.c", Status.PASS)]
    report = compute_setup_score(results=results, overrides={})
    assert report.total == 100.0


def test_setup_score_fail_is_100_for_setup():
    """A failed quality check still means setup is satisfied — infrastructure ran."""
    results = [_result("a.b.c", Status.FAIL)]
    report = compute_setup_score(results=results, overrides={})
    assert report.total == 100.0


def test_setup_score_setup_unmet_is_0():
    results = [_result("a.b.c", Status.SETUP_UNMET)]
    report = compute_setup_score(results=results, overrides={})
    assert report.total == 0.0


def test_setup_score_override_counts_as_pass():
    """A control in overrides counts as 100 even if status was setup-unmet."""
    results = [_result("a.b.c", Status.SETUP_UNMET)]
    overrides = {"a.b.c": OverrideEntry(reason="x", decided_at="2026-04-19")}
    report = compute_setup_score(results=results, overrides=overrides)
    assert report.total == 100.0


def test_setup_score_per_domain_average():
    """Per-domain score = average of its controls. Total = average of domains."""
    results = [
        _result("a.docs.x", Status.PASS),         # 100
        _result("a.docs.y", Status.SETUP_UNMET),  # 0   → docs avg = 50
        _result("a.security.z", Status.PASS),     # 100 → security avg = 100
    ]
    report = compute_setup_score(results=results, overrides={})
    assert report.per_domain == {"docs": 50.0, "security": 100.0}
    # Total = avg of domains = (50 + 100) / 2 = 75
    assert report.total == 75.0


def test_setup_score_empty_results():
    """Empty results → total is 0 (or sentinel; pick 0)."""
    report = compute_setup_score(results=[], overrides={})
    assert report.total == 0.0
    assert report.per_domain == {}


def test_setup_score_report_includes_per_control():
    """Report carries the per-control 100/0 mapping for the formatter to consume."""
    results = [
        _result("a.docs.x", Status.PASS),
        _result("a.docs.y", Status.SETUP_UNMET),
    ]
    report = compute_setup_score(results=results, overrides={})
    assert report.per_control["a.docs.x"] == 100.0
    assert report.per_control["a.docs.y"] == 0.0
```

- [ ] **Step 2: Run — verify FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_verify_score_setup.py -v
```

Expected: 7 tests fail on import.

- [ ] **Step 3: Implement score.py**

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/verify/score.py`:

```python
"""Setup + Quality score formulas per spec §7.

Setup score: per-control 100 if status is pass/fail OR control is overridden,
else 0. Per-domain mean. Total mean of domains.

Quality score (Task 4): per-control 100 if pass / 0 if fail / EXCLUDED if
setup-unmet. Per-domain mean of measurable. Total mean of domains.
"""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass, field

from agent_weiss.lib.contract import Status
from agent_weiss.lib.setup.types import OverrideEntry
from agent_weiss.lib.verify.types import ControlResult


@dataclass(frozen=True)
class ScoreReport:
    """Computed score breakdown.

    per_control: control_id → score (0..100). Excluded controls (quality
        score with setup-unmet) are absent from this map.
    per_domain: domain → mean of per_control scores in that domain.
    total: mean of per_domain scores. 0.0 when there are no measurable
        controls/domains.
    """
    per_control: dict[str, float] = field(default_factory=dict)
    per_domain: dict[str, float] = field(default_factory=dict)
    total: float = 0.0


def compute_setup_score(
    *,
    results: list[ControlResult],
    overrides: dict[str, OverrideEntry],
) -> ScoreReport:
    """Compute the Setup score per spec §7.

    Per control: 100 if status is pass/fail OR control is in overrides; 0 if
    status is setup-unmet (and not overridden).
    """
    per_control: OrderedDict[str, float] = OrderedDict()
    for r in results:
        if r.control_id in overrides:
            per_control[r.control_id] = 100.0
        elif r.status in (Status.PASS, Status.FAIL):
            per_control[r.control_id] = 100.0
        else:  # SETUP_UNMET
            per_control[r.control_id] = 0.0

    return _aggregate(per_control, results)


def _aggregate(
    per_control: dict[str, float],
    results: list[ControlResult],
) -> ScoreReport:
    """Roll per_control scores up to per_domain mean and total mean."""
    if not per_control:
        return ScoreReport()

    # Build domain → list of scores from per_control.
    by_domain: OrderedDict[str, list[float]] = OrderedDict()
    cid_to_domain = {r.control_id: r.domain for r in results}
    for cid, score in per_control.items():
        domain = cid_to_domain[cid]
        by_domain.setdefault(domain, []).append(score)

    per_domain = {d: sum(s) / len(s) for d, s in by_domain.items()}
    total = sum(per_domain.values()) / len(per_domain)
    return ScoreReport(per_control=dict(per_control), per_domain=per_domain, total=total)
```

- [ ] **Step 4: Run — PASS**

```bash
uv run pytest -v
```

Expected: 7 new pass; total 216 (209 + 7).

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/verify/score.py tests/test_verify_score_setup.py
git commit -m "feat: setup score formula"
git push
```

---

## Task 4: Quality score

**Files:**
- Modify: `src/agent_weiss/lib/verify/score.py` (add compute_quality_score)
- Create: `tests/test_verify_score_quality.py`

The Quality score has different rules: setup-unmet controls are EXCLUDED (not counted as 0), and overridden controls count as 100.

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_verify_score_quality.py`:

```python
"""Tests for quality scoring."""
from agent_weiss.lib.contract import Status
from agent_weiss.lib.verify.types import ControlResult
from agent_weiss.lib.verify.score import compute_quality_score, ScoreReport
from agent_weiss.lib.setup.types import OverrideEntry


def _result(cid: str, status: Status) -> ControlResult:
    return ControlResult(
        control_id=cid,
        profile=cid.split(".")[0],
        domain=cid.split(".")[1],
        status=status,
        summary="x",
    )


def test_quality_pass_is_100():
    results = [_result("a.b.c", Status.PASS)]
    report = compute_quality_score(results=results, overrides={})
    assert report.total == 100.0


def test_quality_fail_is_0():
    results = [_result("a.b.c", Status.FAIL)]
    report = compute_quality_score(results=results, overrides={})
    assert report.total == 0.0


def test_quality_setup_unmet_is_excluded():
    """Setup-unmet controls are not counted at all (don't penalize quality)."""
    results = [
        _result("a.b.c", Status.PASS),
        _result("a.b.d", Status.SETUP_UNMET),
    ]
    report = compute_quality_score(results=results, overrides={})
    # Only c is measurable → 100
    assert report.total == 100.0
    assert "a.b.d" not in report.per_control


def test_quality_override_counts_as_pass():
    """Overridden controls count as 100 in quality (the user's call is final)."""
    results = [_result("a.b.c", Status.SETUP_UNMET)]
    overrides = {"a.b.c": OverrideEntry(reason="x", decided_at="2026-04-19")}
    report = compute_quality_score(results=results, overrides=overrides)
    assert report.total == 100.0
    assert report.per_control["a.b.c"] == 100.0


def test_quality_per_domain_excludes_unmeasurable():
    """A domain with all setup-unmet controls is excluded from the total."""
    results = [
        _result("a.docs.x", Status.PASS),         # docs measurable: 100
        _result("a.security.y", Status.SETUP_UNMET),  # security: no measurable
        _result("a.security.z", Status.SETUP_UNMET),
    ]
    report = compute_quality_score(results=results, overrides={})
    # Only docs in per_domain
    assert "docs" in report.per_domain
    assert "security" not in report.per_domain
    assert report.total == 100.0


def test_quality_mixed_per_domain():
    """Mixed pass/fail in a domain averages; setup-unmet excluded from that average."""
    results = [
        _result("a.docs.x", Status.PASS),         # 100
        _result("a.docs.y", Status.FAIL),         # 0
        _result("a.docs.z", Status.SETUP_UNMET),  # excluded
    ]
    # docs avg of measurable: (100 + 0) / 2 = 50
    report = compute_quality_score(results=results, overrides={})
    assert report.per_domain["docs"] == 50.0


def test_quality_empty_results():
    report = compute_quality_score(results=[], overrides={})
    assert report.total == 0.0
    assert report.per_domain == {}
```

- [ ] **Step 2: Run — verify FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_verify_score_quality.py -v
```

Expected: 7 tests fail on `compute_quality_score` import.

- [ ] **Step 3: Append to score.py**

Append to `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/verify/score.py`:

```python


def compute_quality_score(
    *,
    results: list[ControlResult],
    overrides: dict[str, OverrideEntry],
) -> ScoreReport:
    """Compute the Quality score per spec §7.

    Per control: 100 if pass; 0 if fail; EXCLUDED if setup-unmet (and not
    overridden). Overrides count as 100.

    Per domain: mean of measurable controls. Domains with no measurable
    controls are excluded from the total.
    """
    per_control: OrderedDict[str, float] = OrderedDict()
    for r in results:
        if r.control_id in overrides:
            per_control[r.control_id] = 100.0
            continue
        if r.status is Status.PASS:
            per_control[r.control_id] = 100.0
        elif r.status is Status.FAIL:
            per_control[r.control_id] = 0.0
        # SETUP_UNMET (without override) → excluded

    return _aggregate(per_control, results)
```

- [ ] **Step 4: Run — PASS**

```bash
uv run pytest -v
```

Expected: 7 new pass; total 223 (216 + 7).

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/verify/score.py tests/test_verify_score_quality.py
git commit -m "feat: quality score formula"
git push
```

---

## Task 5: Report formatter

**Files:**
- Create: `src/agent_weiss/lib/verify/report.py`
- Create: `tests/test_verify_report.py`

Generate the human-readable markdown report. Includes overall scores, per-domain breakdown, per-control checkmark + summary.

- [ ] **Step 1: Write failing test**

Create `/Users/iorlas/Workspaces/agent-weiss/tests/test_verify_report.py`:

```python
"""Tests for verify report formatter."""
from agent_weiss.lib.contract import Status
from agent_weiss.lib.verify.types import ControlResult
from agent_weiss.lib.verify.score import compute_setup_score, compute_quality_score
from agent_weiss.lib.verify.report import format_report
from agent_weiss.lib.setup.types import OverrideEntry


def _result(cid: str, status: Status, summary: str = "x", findings_count: int = 0, install: str | None = None) -> ControlResult:
    return ControlResult(
        control_id=cid,
        profile=cid.split(".")[0],
        domain=cid.split(".")[1],
        status=status,
        summary=summary,
        findings_count=findings_count,
        install=install,
    )


def test_report_contains_overall_scores():
    results = [
        _result("u.docs.x", Status.PASS),
        _result("u.security.y", Status.FAIL),
    ]
    setup = compute_setup_score(results=results, overrides={})
    quality = compute_quality_score(results=results, overrides={})
    text = format_report(
        results=results, setup_score=setup, quality_score=quality, overrides={}
    )
    assert "Setup" in text
    assert "Quality" in text
    # Setup: both pass+fail count as 100 → 100; Quality: 100+0 across two
    # domains → 50.
    assert "100" in text  # somewhere in the setup line
    assert "50" in text   # somewhere in the quality line


def test_report_lists_each_control_with_status_marker():
    results = [
        _result("u.docs.x", Status.PASS, "AGENTS.md present"),
        _result("u.docs.y", Status.FAIL, "missing CLAUDE.md", findings_count=1),
        _result("u.docs.z", Status.SETUP_UNMET, "conftest not installed", install="brew install conftest"),
    ]
    setup = compute_setup_score(results=results, overrides={})
    quality = compute_quality_score(results=results, overrides={})
    text = format_report(
        results=results, setup_score=setup, quality_score=quality, overrides={}
    )
    # Pass marker (some sort of ✓ or [PASS])
    assert "u.docs.x" in text
    # Fail marker + summary
    assert "u.docs.y" in text
    assert "missing CLAUDE.md" in text
    # Setup-unmet shows install hint
    assert "u.docs.z" in text
    assert "brew install conftest" in text


def test_report_groups_controls_by_domain():
    results = [
        _result("u.docs.x", Status.PASS),
        _result("u.security.y", Status.PASS),
        _result("u.docs.z", Status.PASS),
    ]
    setup = compute_setup_score(results=results, overrides={})
    quality = compute_quality_score(results=results, overrides={})
    text = format_report(
        results=results, setup_score=setup, quality_score=quality, overrides={}
    )
    docs_pos = text.lower().index("docs")
    security_pos = text.lower().index("security")
    x_pos = text.index("u.docs.x")
    y_pos = text.index("u.security.y")
    z_pos = text.index("u.docs.z")
    # Both docs items appear before the security header
    assert docs_pos < x_pos < z_pos < security_pos < y_pos


def test_report_marks_overridden_controls():
    results = [
        _result("u.docs.x", Status.SETUP_UNMET),
    ]
    overrides = {"u.docs.x": OverrideEntry(reason="we use mypy", decided_at="2026-04-19")}
    setup = compute_setup_score(results=results, overrides=overrides)
    quality = compute_quality_score(results=results, overrides=overrides)
    text = format_report(
        results=results, setup_score=setup, quality_score=quality, overrides=overrides
    )
    assert "we use mypy" in text or "override" in text.lower()


def test_report_empty_results():
    setup = compute_setup_score(results=[], overrides={})
    quality = compute_quality_score(results=[], overrides={})
    text = format_report(
        results=[], setup_score=setup, quality_score=quality, overrides={}
    )
    assert text.strip()
```

- [ ] **Step 2: Run — FAIL**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest tests/test_verify_report.py -v
```

Expected: 5 tests fail on import.

- [ ] **Step 3: Implement report.py**

Create `/Users/iorlas/Workspaces/agent-weiss/src/agent_weiss/lib/verify/report.py`:

```python
"""Format the verify-phase report as markdown.

Layout:
    # agent-weiss verify report

    **Setup:** 87% (per-domain: docs 100%, security 67%)
    **Quality:** 92% (per-domain: docs 100%, security 50%)

    ## docs
    - ✓ universal.docs.agents-md-present — AGENTS.md present
    - ✓ universal.docs.claude-md-present — CLAUDE.md present
    - ✗ universal.docs.readme-present — fail: no README.* found

    ## security
    - ⚠ universal.security.gitignore-secrets — setup-unmet: conftest not installed
      Install: brew install conftest
    - ⊘ universal.security.gitleaks-precommit — override: we don't use pre-commit
    ...
"""
from __future__ import annotations
from collections import OrderedDict

from agent_weiss.lib.contract import Status
from agent_weiss.lib.setup.types import OverrideEntry
from agent_weiss.lib.verify.types import ControlResult
from agent_weiss.lib.verify.score import ScoreReport


def format_report(
    *,
    results: list[ControlResult],
    setup_score: ScoreReport,
    quality_score: ScoreReport,
    overrides: dict[str, OverrideEntry],
) -> str:
    """Render verify results + scores as a markdown report."""
    lines: list[str] = ["# agent-weiss verify report", ""]

    if not results:
        lines.append("No applicable controls were checked.")
        return "\n".join(lines) + "\n"

    # Overall scores
    lines.append(f"**Setup:** {round(setup_score.total)}% — per-domain: {_format_per_domain(setup_score)}")
    lines.append(f"**Quality:** {round(quality_score.total)}% — per-domain: {_format_per_domain(quality_score)}")
    lines.append("")

    # Per-domain breakdown
    by_domain: OrderedDict[str, list[ControlResult]] = OrderedDict()
    for r in results:
        by_domain.setdefault(r.domain, []).append(r)

    for domain, items in by_domain.items():
        lines.append(f"## {domain}")
        for r in items:
            marker, descriptor = _marker_and_descriptor(r, overrides)
            lines.append(f"- {marker} {r.control_id} — {descriptor}")
            if r.status is Status.SETUP_UNMET and r.install and r.control_id not in overrides:
                lines.append(f"  Install: {r.install}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _format_per_domain(score: ScoreReport) -> str:
    """Render per-domain scores like 'docs 100%, security 67%'."""
    if not score.per_domain:
        return "(no domains)"
    return ", ".join(
        f"{domain} {round(value)}%" for domain, value in score.per_domain.items()
    )


def _marker_and_descriptor(
    result: ControlResult,
    overrides: dict[str, OverrideEntry],
) -> tuple[str, str]:
    """Return (marker glyph, descriptor) for a control result."""
    if result.control_id in overrides:
        return "⊘", f"override: {overrides[result.control_id].reason}"
    if result.status is Status.PASS:
        return "✓", result.summary
    if result.status is Status.FAIL:
        return "✗", f"fail: {result.summary}"
    # SETUP_UNMET
    return "⚠", f"setup-unmet: {result.summary}"
```

- [ ] **Step 4: Run — PASS**

```bash
uv run pytest -v
```

Expected: 5 new pass; total 228 (223 + 5).

- [ ] **Step 5: Commit**

```bash
git add src/agent_weiss/lib/verify/report.py tests/test_verify_report.py
git commit -m "feat: verify report formatter"
git push
```

---

## Task 6: skill.md verify + score + report wiring

**Files:**
- Modify: `/Users/iorlas/Workspaces/agent-weiss/.claude/skills/agent-weiss/SKILL.md`

Replace sections 5 (Verify phase) and 6 (Score and report) with concrete invocations of the new helpers.

- [ ] **Step 1: Read current SKILL.md**

```bash
cat /Users/iorlas/Workspaces/agent-weiss/.claude/skills/agent-weiss/SKILL.md
```

Locate the `### 5. Verify phase` and `### 6. Score and report` headings.

- [ ] **Step 2: Replace section 5 (Verify phase)**

Find `### 5. Verify phase` and replace its body (everything between `### 5. Verify phase` and `### 6. Score and report`) with:

```markdown
### 5. Verify phase

Run every applicable control's `check.sh` against the project. Sequential
execution; per-control timeout enforced by the shell, not by us.

```python
from pathlib import Path
from agent_weiss.lib.state import read_state
from agent_weiss.lib.bundle import resolve_bundle_root
from agent_weiss.lib.verify.dispatch import run_all_checks

project_root = Path("<project_root>")
state = read_state(project_root)
bundle = resolve_bundle_root()

results = run_all_checks(
    project_root=project_root,
    bundle_root=bundle,
    state=state,
)
```

`results` is a list of `ControlResult`. Each carries `control_id`, `profile`,
`domain`, `status` (`pass` / `fail` / `setup-unmet`), `summary`,
`findings_count`, and (for setup-unmet) `install`.

> Important: invoke this AFTER the Setup phase — per spec, the user has had
> a chance to fix anything outstanding before scoring kicks in.

```

- [ ] **Step 3: Replace section 6 (Score and report)**

Find `### 6. Score and report` and replace its body (everything between `### 6. Score and report` and `### 7. Update state`) with:

```markdown
### 6. Score and report

Compute the two scores and print the report.

```python
from agent_weiss.lib.verify.score import compute_setup_score, compute_quality_score
from agent_weiss.lib.verify.report import format_report

setup_score = compute_setup_score(results=results, overrides=state.overrides)
quality_score = compute_quality_score(results=results, overrides=state.overrides)

report_text = format_report(
    results=results,
    setup_score=setup_score,
    quality_score=quality_score,
    overrides=state.overrides,
)
print(report_text)
```

Per the roadmap: scores are re-evaluated each run, never cached. Don't write
them into `.agent-weiss.yaml`.

The report uses these glyphs:
- `✓` — control passed
- `✗` — control failed (followed by summary + findings_count)
- `⚠` — setup-unmet (followed by install hint)
- `⊘` — overridden (followed by user's reason)

```

- [ ] **Step 4: Verify pytest still passes**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest -v
```

Expected: 228 tests (no test changes in this task).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/agent-weiss/SKILL.md
git commit -m "docs: skill.md verify + score + report wiring"
git push
```

---

## Task 7: Roadmap update + tag milestone

**Files:**
- Modify: `/Users/iorlas/Workspaces/agent-harness/docs/superpowers/plans/2026-04-14-agent-weiss-roadmap.md`

- [ ] **Step 1: Update roadmap status**

Edit the roadmap. Change Plan 4's `Status` from `Pending` to `Done`. Don't change Plans 5/6 (still Pending).

```bash
cd /Users/iorlas/Workspaces/agent-harness
git add docs/superpowers/plans/2026-04-14-agent-weiss-roadmap.md
git commit -m "roadmap: mark agent-weiss Plan 4 (Verify Workflow & Scoring) complete"
git push
```

- [ ] **Step 2: Tag the milestone**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
git tag -a verify-scoring -m "Plan 4 complete: verify dispatcher + setup/quality scores + report formatter"
git push origin verify-scoring
```

- [ ] **Step 3: Final sanity check**

```bash
cd /Users/iorlas/Workspaces/agent-weiss
uv run pytest -v 2>&1 | tail -5
gh run list --repo yoselabs/agent-weiss --limit 1
git tag --list | grep -E '(foundations|control|setup|verify)'
```

Expected:
- All tests pass (~228)
- Latest CI run = `success`
- Tags listed: `foundations-mvp`, `control-library`, `setup-workflow`, `verify-scoring`

---

## Plan-completion checklist

Before declaring Plan 4 done:
- [ ] All 7 tasks committed and pushed
- [ ] CI green on `main`
- [ ] `uv run pytest -v` passes locally with all 228 tests
- [ ] All Rego policies still pass `conftest verify`
- [ ] Roadmap updated in agent-harness repo: Plan 4 → Done
- [ ] Tag `verify-scoring` pushed
- [ ] No TODO / TBD markers in new code

## After Plan 4 completes

The user loop is now fully wired in skill.md:
- Detect → Reconcile (P3) → Confirm profiles → Setup phase (P3) → Verify phase (P4) → Score + Report (P4) → Update state

Two paths forward:
- **Plan 5: Distribution Packaging** — package the bundle for Claude marketplace + PyPI + npm. Involves manifest, install scripts, CI publish workflows. Unblocks real-world usage.
- **Plan 4.5 (optional follow-up):** Refine `compute_proposals` to be driven by verify results so the user only sees actionable proposals (failing or setup-unmet, not all applicable). This is a UX improvement, not a structural change.

Plan 6 (Drift Refresh) depends on Plan 5 being done (needs install location to compare against).
