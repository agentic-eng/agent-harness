# CLAUDE.md Adaptive Audit + Security Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CLAUDE.md adaptive audit (init check + skill guidance) and a new `agent-harness security-audit` command that blocks only when a newly-added dependency has a High/Critical CVE with a fix available.

**Architecture:** Feature 1 adds a setup check to the universal preset that flags existing CLAUDE.md for skill-based review, plus skill guidance for AI agents to audit CLAUDE.md content. Feature 2 adds a standalone `security/` module (not in the preset system) with dep-diff detection, tool runners (pip-audit, npm audit), and a policy engine. A new CLI command orchestrates it.

**Tech Stack:** Python 3.11+, Click (CLI), tomlkit (TOML parsing), subprocess (git diff, pip-audit, npm audit), JSON parsing for audit output.

---

## Feature 1: CLAUDE.md Adaptive Audit

### Task 1: CLAUDE.md Init Setup Check

**Files:**
- Create: `src/agent_harness/presets/universal/claudemd_setup.py`
- Modify: `src/agent_harness/presets/universal/__init__.py:58-65`
- Test: `tests/presets/universal/test_claudemd_setup.py`

- [ ] **Step 1: Write failing tests**

Create `tests/presets/universal/test_claudemd_setup.py`:

```python
from pathlib import Path

from agent_harness.presets.universal.claudemd_setup import check_claudemd_setup


def test_no_claudemd_returns_no_issues(tmp_path: Path):
    """No CLAUDE.md at all — scaffold will create it, no setup issue needed."""
    issues = check_claudemd_setup(tmp_path)
    assert issues == []


def test_claudemd_exists_returns_recommendation(tmp_path: Path):
    """Existing CLAUDE.md should get a recommendation to audit via skill."""
    (tmp_path / "CLAUDE.md").write_text("# My Project\n\nSome custom instructions.\n")
    issues = check_claudemd_setup(tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "recommendation"
    assert "skill" in issues[0].message.lower() or "audit" in issues[0].message.lower()
    assert issues[0].fix is None  # Not auto-fixable — needs AI judgment


def test_claudemd_with_make_check_returns_no_issues(tmp_path: Path):
    """CLAUDE.md that already mentions make check — no issue."""
    (tmp_path / "CLAUDE.md").write_text(
        "# My Project\n\n## Dev Commands\n\nmake check\nmake lint\n"
    )
    issues = check_claudemd_setup(tmp_path)
    assert issues == []


def test_claudemd_with_agent_harness_lint_returns_no_issues(tmp_path: Path):
    """CLAUDE.md mentioning agent-harness lint is also fine."""
    (tmp_path / "CLAUDE.md").write_text(
        "# My Project\n\nRun `agent-harness lint` before committing.\n"
        "Run `make check` for full gate.\n"
    )
    issues = check_claudemd_setup(tmp_path)
    assert issues == []


def test_claudemd_with_lint_but_no_check(tmp_path: Path):
    """CLAUDE.md mentions lint but not the full check gate — recommend adding."""
    (tmp_path / "CLAUDE.md").write_text(
        "# My Project\n\nRun `make lint` before committing.\n"
    )
    issues = check_claudemd_setup(tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "recommendation"
    assert "make check" in issues[0].message.lower() or "workflow" in issues[0].message.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/presets/universal/test_claudemd_setup.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement the setup check**

Create `src/agent_harness/presets/universal/claudemd_setup.py`:

```python
"""CLAUDE.md setup check — flag existing CLAUDE.md for skill-based audit."""

from __future__ import annotations

from pathlib import Path

from agent_harness.setup_check import SetupIssue

# Key phrases that indicate the CLAUDE.md has workflow instructions.
# We check for the presence of a "full gate" concept (make check or equivalent)
# AND at least one lint reference (make lint or agent-harness lint).
_GATE_PHRASES = ["make check", "make lint", "agent-harness lint", "agent-harness fix"]
_FULL_GATE_PHRASES = ["make check"]


def check_claudemd_setup(project_dir: Path) -> list[SetupIssue]:
    """Check CLAUDE.md for presence of key workflow instructions."""
    claudemd_path = project_dir / "CLAUDE.md"
    if not claudemd_path.exists():
        return []  # Scaffold will create it

    content = claudemd_path.read_text().lower()

    # Check if CLAUDE.md mentions the full quality gate
    has_full_gate = any(phrase in content for phrase in _FULL_GATE_PHRASES)
    has_any_lint = any(phrase in content for phrase in _GATE_PHRASES)

    if has_full_gate and has_any_lint:
        return []  # Looks good

    if has_any_lint and not has_full_gate:
        return [
            SetupIssue(
                file="CLAUDE.md",
                message=(
                    "mentions lint but not `make check` — "
                    "run the agent-harness skill to audit workflow instructions"
                ),
                severity="recommendation",
            )
        ]

    # Has CLAUDE.md but no workflow instructions at all
    return [
        SetupIssue(
            file="CLAUDE.md",
            message=(
                "exists but missing workflow instructions — "
                "run the agent-harness skill to audit and add dev commands"
            ),
            severity="recommendation",
        )
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/presets/universal/test_claudemd_setup.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Wire into UniversalPreset.run_setup()**

In `src/agent_harness/presets/universal/__init__.py`, add the import and call inside `run_setup()`:

```python
def run_setup(self, project_dir: Path, config: dict) -> list[SetupIssue]:
    from .claudemd_setup import check_claudemd_setup
    from .gitignore_setup import check_gitignore_setup

    issues = check_gitignore_setup(
        project_dir,
        stacks=config.get("stacks", set()),
        git_root=config.get("git_root"),
    )
    issues.extend(check_claudemd_setup(project_dir))
    return issues
```

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 7: Run lint**

Run: `uv run ruff format src/agent_harness/presets/universal/claudemd_setup.py tests/presets/universal/test_claudemd_setup.py && agent-harness lint`
Expected: All checks pass

- [ ] **Step 8: Commit**

```bash
git add src/agent_harness/presets/universal/claudemd_setup.py tests/presets/universal/test_claudemd_setup.py src/agent_harness/presets/universal/__init__.py
git commit -m "feat: add CLAUDE.md init setup check for workflow instructions"
```

### Task 2: Update SKILL.md with CLAUDE.md Audit Guidance

**Files:**
- Modify: `skills/agent-harness/SKILL.md`

- [ ] **Step 1: Add CLAUDE.md audit step to the Setup Workflow**

Add a new step between Step 2 (Apply fixes) and Step 3 (Install pre-commit hooks) in `skills/agent-harness/SKILL.md`. The new step is **Step 2.5: Audit CLAUDE.md**:

```markdown
### Step 2.5: Audit CLAUDE.md

Read the project's `CLAUDE.md` (if it exists). Check whether it includes these key workflow instructions. What to look for depends on the detected stacks:

**All projects must mention:**
- `make check` (or equivalent full quality gate command)
- `make lint` or `agent-harness lint`
- `make fix` or `agent-harness fix`
- Pre-commit hooks run automatically
- Never truncate lint/test output

**Python projects should also mention:**
- `make test` (with coverage)
- `make coverage-diff` (diff-cover for changed lines)
- If coverage-diff fails, write tests for uncovered changed lines

**JavaScript projects should also mention:**
- `make test`
- Biome for formatting/linting

**What to do:**
- If CLAUDE.md doesn't exist: `agent-harness init --apply` will create one from template — no action needed.
- If CLAUDE.md exists but is missing key instructions: propose targeted edits that fit the existing document's style and structure. Don't dump a template block — integrate naturally.
- If CLAUDE.md already covers everything: move on.

**Important:** This is an AI judgment call, not a mechanical check. Read the whole file, understand its structure, and add only what's missing in a way that flows with the existing content.
```

- [ ] **Step 2: Commit**

```bash
git add skills/agent-harness/SKILL.md
git commit -m "feat: add CLAUDE.md audit guidance to agent-harness skill"
```

---

## Feature 2: Security Audit Command

### Task 3: Audit Data Models

**Files:**
- Create: `src/agent_harness/security/__init__.py`
- Create: `src/agent_harness/security/models.py`
- Test: `tests/security/test_models.py`
- Create: `tests/security/__init__.py`

- [ ] **Step 1: Write failing tests for data models**

Create `tests/security/__init__.py` (empty).

Create `tests/security/test_models.py`:

```python
from agent_harness.security.models import AuditFinding, Classification, SecurityReport


def test_finding_classification_new_high_fixable_is_fail():
    f = AuditFinding(
        package="evil-pkg",
        version="1.0.0",
        vuln_id="CVE-2026-1234",
        severity="high",
        description="RCE vulnerability",
        fix_versions=["1.0.1"],
        is_new_dep=True,
    )
    assert f.classify() == Classification.FAIL


def test_finding_classification_new_critical_fixable_is_fail():
    f = AuditFinding(
        package="evil-pkg",
        version="1.0.0",
        vuln_id="CVE-2026-5678",
        severity="critical",
        description="SQL injection",
        fix_versions=["2.0.0"],
        is_new_dep=True,
    )
    assert f.classify() == Classification.FAIL


def test_finding_classification_new_high_no_fix_is_warn():
    f = AuditFinding(
        package="evil-pkg",
        version="1.0.0",
        vuln_id="CVE-2026-9999",
        severity="high",
        description="No fix yet",
        fix_versions=[],
        is_new_dep=True,
    )
    assert f.classify() == Classification.WARN


def test_finding_classification_existing_high_fixable_is_warn():
    f = AuditFinding(
        package="old-pkg",
        version="1.0.0",
        vuln_id="CVE-2025-1111",
        severity="high",
        description="Known issue in existing dep",
        fix_versions=["1.1.0"],
        is_new_dep=False,
    )
    assert f.classify() == Classification.WARN


def test_finding_classification_new_low_fixable_is_warn():
    f = AuditFinding(
        package="some-pkg",
        version="1.0.0",
        vuln_id="CVE-2026-2222",
        severity="low",
        description="Minor info leak",
        fix_versions=["1.0.1"],
        is_new_dep=True,
    )
    assert f.classify() == Classification.WARN


def test_finding_classification_new_medium_fixable_is_warn():
    f = AuditFinding(
        package="med-pkg",
        version="2.0.0",
        vuln_id="CVE-2026-3333",
        severity="medium",
        description="XSS",
        fix_versions=["2.0.1"],
        is_new_dep=True,
    )
    assert f.classify() == Classification.WARN


def test_report_has_failures():
    findings = [
        AuditFinding("pkg", "1.0", "CVE-1", "high", "bad", ["1.1"], is_new_dep=True),
        AuditFinding("pkg2", "1.0", "CVE-2", "low", "meh", ["1.1"], is_new_dep=False),
    ]
    report = SecurityReport(findings=findings, ignored_ids=set())
    assert report.has_failures is True
    assert report.fail_count == 1
    assert report.warn_count == 1


def test_report_no_failures():
    findings = [
        AuditFinding("pkg", "1.0", "CVE-1", "low", "meh", ["1.1"], is_new_dep=True),
    ]
    report = SecurityReport(findings=findings, ignored_ids=set())
    assert report.has_failures is False
    assert report.fail_count == 0
    assert report.warn_count == 1


def test_report_ignores_cves():
    findings = [
        AuditFinding("pkg", "1.0", "CVE-1", "high", "bad", ["1.1"], is_new_dep=True),
    ]
    report = SecurityReport(findings=findings, ignored_ids={"CVE-1"})
    assert report.has_failures is False
    assert report.fail_count == 0
    assert report.warn_count == 0
    assert report.ignored_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/security/test_models.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement data models**

Create `src/agent_harness/security/__init__.py` (empty).

Create `src/agent_harness/security/models.py`:

```python
"""Security audit data models and classification policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Classification(Enum):
    """How a vulnerability finding should be treated."""

    FAIL = "fail"  # Blocks the audit
    WARN = "warn"  # Informational only
    IGNORED = "ignored"  # Explicitly suppressed


@dataclass
class AuditFinding:
    """A single vulnerability found by an audit tool."""

    package: str
    version: str
    vuln_id: str
    severity: str  # "critical" | "high" | "medium" | "low" | "unknown"
    description: str
    fix_versions: list[str]
    is_new_dep: bool = False

    def classify(self) -> Classification:
        """Apply the security policy: only FAIL on new + high/critical + fix available."""
        has_fix = len(self.fix_versions) > 0
        is_high = self.severity in ("high", "critical")
        if self.is_new_dep and is_high and has_fix:
            return Classification.FAIL
        return Classification.WARN


@dataclass
class SecurityReport:
    """Aggregated results from a security audit run."""

    findings: list[AuditFinding]
    ignored_ids: set[str] = field(default_factory=set)

    def _active_findings(self) -> list[tuple[AuditFinding, Classification]]:
        result = []
        for f in self.findings:
            if f.vuln_id in self.ignored_ids:
                continue
            result.append((f, f.classify()))
        return result

    @property
    def has_failures(self) -> bool:
        return any(c == Classification.FAIL for _, c in self._active_findings())

    @property
    def fail_count(self) -> int:
        return sum(1 for _, c in self._active_findings() if c == Classification.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for _, c in self._active_findings() if c == Classification.WARN)

    @property
    def ignored_count(self) -> int:
        return sum(1 for f in self.findings if f.vuln_id in self.ignored_ids)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/security/test_models.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff format src/agent_harness/security/ tests/security/
git add src/agent_harness/security/__init__.py src/agent_harness/security/models.py tests/security/__init__.py tests/security/test_models.py
git commit -m "feat: add security audit data models and classification policy"
```

### Task 4: Dependency Diff Detection

**Files:**
- Create: `src/agent_harness/security/dep_diff.py`
- Test: `tests/security/test_dep_diff.py`

- [ ] **Step 1: Write failing tests for Python dep parsing**

Create `tests/security/test_dep_diff.py`:

```python
import subprocess
from pathlib import Path

import pytest

from agent_harness.security.dep_diff import (
    detect_new_deps,
    parse_js_deps,
    parse_python_deps,
)


def test_parse_python_deps_project_dependencies():
    content = """\
[project]
dependencies = ["requests>=2.0", "click~=8.0", "rich"]
"""
    assert parse_python_deps(content) == {"requests", "click", "rich"}


def test_parse_python_deps_optional_and_groups():
    content = """\
[project]
dependencies = ["flask"]

[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff"]

[dependency-groups]
test = ["coverage", "pytest-cov"]
"""
    deps = parse_python_deps(content)
    assert deps == {"flask", "pytest", "ruff", "coverage", "pytest-cov"}


def test_parse_python_deps_empty():
    content = "[project]\nname = 'foo'\n"
    assert parse_python_deps(content) == set()


def test_parse_python_deps_extras_in_name():
    """Dep specifier with extras like 'package[extra]>=1.0'."""
    content = """\
[project]
dependencies = ["uvicorn[standard]>=0.20", "boto3"]
"""
    assert parse_python_deps(content) == {"uvicorn", "boto3"}


def test_parse_js_deps():
    content = """\
{
  "dependencies": {"react": "^18.0", "next": "^14.0"},
  "devDependencies": {"jest": "^29.0", "eslint": "^8.0"}
}
"""
    assert parse_js_deps(content) == {"react", "next", "jest", "eslint"}


def test_parse_js_deps_empty():
    content = '{"name": "foo"}'
    assert parse_js_deps(content) == set()


def test_parse_js_deps_peer_and_optional():
    content = """\
{
  "dependencies": {"a": "1"},
  "peerDependencies": {"b": "2"},
  "optionalDependencies": {"c": "3"}
}
"""
    assert parse_js_deps(content) == {"a", "b", "c"}


@pytest.fixture()
def git_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    return tmp_path


def test_detect_new_deps_python(git_repo: Path):
    """New dep added after base branch should be detected."""
    # Create base with one dep
    pyproject = git_repo / "pyproject.toml"
    pyproject.write_text('[project]\ndependencies = ["requests"]\n')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(git_repo), capture_output=True
    )
    subprocess.run(
        ["git", "branch", "main"], cwd=str(git_repo), capture_output=True
    )

    # Add a new dep on working branch
    pyproject.write_text('[project]\ndependencies = ["requests", "evil-pkg"]\n')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add dep"], cwd=str(git_repo), capture_output=True
    )

    new_deps = detect_new_deps(git_repo, base_branch="main")
    assert new_deps == {"evil-pkg"}


def test_detect_new_deps_no_base_branch(git_repo: Path):
    """If base branch doesn't exist, all deps are treated as new."""
    pyproject = git_repo / "pyproject.toml"
    pyproject.write_text('[project]\ndependencies = ["requests"]\n')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(git_repo), capture_output=True
    )

    new_deps = detect_new_deps(git_repo, base_branch="main")
    assert new_deps == {"requests"}


def test_detect_new_deps_js(git_repo: Path):
    """New JS dep added after base branch should be detected."""
    pkg = git_repo / "package.json"
    pkg.write_text('{"dependencies": {"react": "^18.0"}}')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(git_repo), capture_output=True
    )
    subprocess.run(
        ["git", "branch", "main"], cwd=str(git_repo), capture_output=True
    )

    pkg.write_text('{"dependencies": {"react": "^18.0", "evil-js": "^1.0"}}')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add dep"], cwd=str(git_repo), capture_output=True
    )

    new_deps = detect_new_deps(git_repo, base_branch="main")
    assert new_deps == {"evil-js"}


def test_detect_new_deps_upgrade_not_new(git_repo: Path):
    """Upgrading an existing dep version should NOT count as new."""
    pyproject = git_repo / "pyproject.toml"
    pyproject.write_text('[project]\ndependencies = ["requests>=2.0"]\n')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(git_repo), capture_output=True
    )
    subprocess.run(
        ["git", "branch", "main"], cwd=str(git_repo), capture_output=True
    )

    # Upgrade version constraint — same package name
    pyproject.write_text('[project]\ndependencies = ["requests>=3.0"]\n')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "bump"], cwd=str(git_repo), capture_output=True
    )

    new_deps = detect_new_deps(git_repo, base_branch="main")
    assert new_deps == set()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/security/test_dep_diff.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement dep diff detection**

Create `src/agent_harness/security/dep_diff.py`:

```python
"""Dependency diff detection — find newly added packages vs a base branch."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]


def parse_python_deps(content: str) -> set[str]:
    """Extract dependency names from pyproject.toml content."""
    data = tomllib.loads(content)
    deps: set[str] = set()

    # [project.dependencies]
    for dep in data.get("project", {}).get("dependencies", []):
        name = _extract_python_dep_name(dep)
        if name:
            deps.add(name)

    # [project.optional-dependencies]
    for group_deps in data.get("project", {}).get("optional-dependencies", {}).values():
        for dep in group_deps:
            name = _extract_python_dep_name(dep)
            if name:
                deps.add(name)

    # [dependency-groups] (PEP 735)
    for group_deps in data.get("dependency-groups", {}).values():
        for dep in group_deps:
            if isinstance(dep, str):
                name = _extract_python_dep_name(dep)
                if name:
                    deps.add(name)

    return deps


def _extract_python_dep_name(specifier: str) -> str | None:
    """Extract normalized package name from a PEP 508 dependency specifier."""
    match = re.match(r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)", specifier)
    if not match:
        return None
    # Normalize: lowercase, hyphens to hyphens (canonical form)
    return match.group(1).lower().replace("_", "-")


def parse_js_deps(content: str) -> set[str]:
    """Extract dependency names from package.json content."""
    data = json.loads(content)
    deps: set[str] = set()
    for key in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        deps.update(data.get(key, {}).keys())
    return deps


def _get_base_file(base_branch: str, file_path: str, project_dir: Path) -> str | None:
    """Get file content from base branch via git show."""
    result = subprocess.run(
        ["git", "show", f"{base_branch}:{file_path}"],
        capture_output=True,
        text=True,
        cwd=str(project_dir),
    )
    if result.returncode != 0:
        return None
    return result.stdout


def detect_new_deps(
    project_dir: Path, base_branch: str = "origin/main"
) -> set[str]:
    """Detect newly added dependencies compared to a base branch.

    Returns set of package names that are in the current working tree
    but not in the base branch. If the base branch doesn't exist or
    the manifest file is new, all current deps are considered new.
    """
    current_deps: set[str] = set()
    base_deps: set[str] = set()

    # Python
    pyproject_path = project_dir / "pyproject.toml"
    if pyproject_path.exists():
        current_deps |= parse_python_deps(pyproject_path.read_text())
        base_content = _get_base_file(base_branch, "pyproject.toml", project_dir)
        if base_content is not None:
            base_deps |= parse_python_deps(base_content)

    # JavaScript
    pkg_json_path = project_dir / "package.json"
    if pkg_json_path.exists():
        current_deps |= parse_js_deps(pkg_json_path.read_text())
        base_content = _get_base_file(base_branch, "package.json", project_dir)
        if base_content is not None:
            base_deps |= parse_js_deps(base_content)

    return current_deps - base_deps
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/security/test_dep_diff.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff format src/agent_harness/security/dep_diff.py tests/security/test_dep_diff.py
git add src/agent_harness/security/dep_diff.py tests/security/test_dep_diff.py
git commit -m "feat: add dependency diff detection for security audit"
```

### Task 5: pip-audit Runner

**Files:**
- Create: `src/agent_harness/security/pip_audit.py`
- Test: `tests/security/test_pip_audit.py`

- [ ] **Step 1: Write failing tests**

Create `tests/security/test_pip_audit.py`:

```python
import json

from agent_harness.security.pip_audit import parse_pip_audit_output
from agent_harness.security.models import AuditFinding


def test_parse_empty_output():
    """No vulnerabilities found."""
    output = json.dumps({"dependencies": [], "fixes": []})
    findings = parse_pip_audit_output(output, new_deps=set())
    assert findings == []


def test_parse_vulnerabilities():
    """Parse pip-audit JSON with vulnerabilities."""
    output = json.dumps({
        "dependencies": [
            {
                "name": "requests",
                "version": "2.25.0",
                "vulns": [
                    {
                        "id": "PYSEC-2026-1",
                        "fix_versions": ["2.25.1"],
                        "aliases": ["CVE-2026-1234"],
                        "description": "SSRF vulnerability",
                    }
                ],
            },
            {
                "name": "flask",
                "version": "2.0.0",
                "vulns": [],
            },
        ],
        "fixes": [],
    })
    findings = parse_pip_audit_output(output, new_deps={"requests"})
    assert len(findings) == 1
    assert findings[0].package == "requests"
    assert findings[0].vuln_id == "PYSEC-2026-1"
    assert findings[0].fix_versions == ["2.25.1"]
    assert findings[0].is_new_dep is True


def test_parse_existing_dep_not_new():
    """Existing dep vulnerabilities should have is_new_dep=False."""
    output = json.dumps({
        "dependencies": [
            {
                "name": "urllib3",
                "version": "1.26.0",
                "vulns": [
                    {
                        "id": "CVE-2026-9999",
                        "fix_versions": [],
                        "aliases": [],
                        "description": "Something",
                    }
                ],
            },
        ],
        "fixes": [],
    })
    findings = parse_pip_audit_output(output, new_deps={"requests"})
    assert len(findings) == 1
    assert findings[0].is_new_dep is False


def test_parse_severity_from_aliases():
    """pip-audit doesn't include severity — default to 'unknown'."""
    output = json.dumps({
        "dependencies": [
            {
                "name": "pkg",
                "version": "1.0",
                "vulns": [
                    {
                        "id": "GHSA-xxxx",
                        "fix_versions": ["1.1"],
                        "aliases": ["CVE-2026-5555"],
                        "description": "Bad stuff",
                    }
                ],
            },
        ],
        "fixes": [],
    })
    findings = parse_pip_audit_output(output, new_deps=set())
    # pip-audit doesn't provide severity natively
    assert findings[0].severity == "unknown"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/security/test_pip_audit.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement pip-audit runner**

Create `src/agent_harness/security/pip_audit.py`:

```python
"""pip-audit runner — parse output and produce AuditFindings."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agent_harness.security.models import AuditFinding


def run_pip_audit(project_dir: Path) -> str | None:
    """Run pip-audit and return JSON output, or None if tool unavailable."""
    # Try uvx first (preferred), then direct pip-audit
    for cmd in [
        ["uvx", "pip-audit", "--format=json", "--output=-"],
        ["pip-audit", "--format=json", "--output=-"],
    ]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(project_dir),
                timeout=120,
            )
            # pip-audit exits 1 when vulns found — that's expected
            if result.stdout:
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def parse_pip_audit_output(
    output: str, new_deps: set[str]
) -> list[AuditFinding]:
    """Parse pip-audit JSON output into AuditFindings."""
    data = json.loads(output)
    findings: list[AuditFinding] = []

    for dep in data.get("dependencies", []):
        pkg_name = dep["name"].lower().replace("_", "-")
        version = dep["version"]
        is_new = pkg_name in new_deps

        for vuln in dep.get("vulns", []):
            findings.append(
                AuditFinding(
                    package=dep["name"],
                    version=version,
                    vuln_id=vuln["id"],
                    severity="unknown",  # pip-audit doesn't provide severity
                    description=vuln.get("description", ""),
                    fix_versions=vuln.get("fix_versions", []),
                    is_new_dep=is_new,
                )
            )

    return findings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/security/test_pip_audit.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff format src/agent_harness/security/pip_audit.py tests/security/test_pip_audit.py
git add src/agent_harness/security/pip_audit.py tests/security/test_pip_audit.py
git commit -m "feat: add pip-audit runner for security audit"
```

### Task 6: npm-audit Runner

**Files:**
- Create: `src/agent_harness/security/npm_audit.py`
- Test: `tests/security/test_npm_audit.py`

- [ ] **Step 1: Write failing tests**

Create `tests/security/test_npm_audit.py`:

```python
import json

from agent_harness.security.npm_audit import parse_npm_audit_output


def test_parse_empty_output():
    output = json.dumps({"vulnerabilities": {}})
    findings = parse_npm_audit_output(output, new_deps=set())
    assert findings == []


def test_parse_vulnerabilities():
    output = json.dumps({
        "vulnerabilities": {
            "lodash": {
                "name": "lodash",
                "severity": "high",
                "via": [
                    {
                        "source": 1234,
                        "name": "lodash",
                        "title": "Prototype Pollution",
                        "url": "https://ghsa.example",
                        "severity": "high",
                        "cwe": ["CWE-1321"],
                        "range": "<4.17.21",
                    }
                ],
                "fixAvailable": True,
            }
        }
    })
    findings = parse_npm_audit_output(output, new_deps={"lodash"})
    assert len(findings) == 1
    assert findings[0].package == "lodash"
    assert findings[0].severity == "high"
    assert findings[0].is_new_dep is True
    assert len(findings[0].fix_versions) > 0


def test_parse_no_fix_available():
    output = json.dumps({
        "vulnerabilities": {
            "old-pkg": {
                "name": "old-pkg",
                "severity": "critical",
                "via": [{"title": "Bad", "severity": "critical", "source": 1}],
                "fixAvailable": False,
            }
        }
    })
    findings = parse_npm_audit_output(output, new_deps=set())
    assert len(findings) == 1
    assert findings[0].fix_versions == []
    assert findings[0].is_new_dep is False


def test_parse_via_string_skipped():
    """When 'via' contains a string (transitive), skip it — only direct vulns."""
    output = json.dumps({
        "vulnerabilities": {
            "transitive-pkg": {
                "name": "transitive-pkg",
                "severity": "moderate",
                "via": ["some-other-pkg"],
                "fixAvailable": True,
            }
        }
    })
    findings = parse_npm_audit_output(output, new_deps=set())
    assert findings == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/security/test_npm_audit.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement npm-audit runner**

Create `src/agent_harness/security/npm_audit.py`:

```python
"""npm-audit runner — parse output and produce AuditFindings."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agent_harness.security.models import AuditFinding


def run_npm_audit(project_dir: Path) -> str | None:
    """Run npm audit and return JSON output, or None if tool unavailable."""
    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True,
            text=True,
            cwd=str(project_dir),
            timeout=120,
        )
        # npm audit exits non-zero when vulns found — that's expected
        if result.stdout:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def parse_npm_audit_output(
    output: str, new_deps: set[str]
) -> list[AuditFinding]:
    """Parse npm audit JSON output into AuditFindings."""
    data = json.loads(output)
    findings: list[AuditFinding] = []

    for pkg_name, vuln_data in data.get("vulnerabilities", {}).items():
        # Skip transitive-only vulns (via contains only strings)
        via_entries = vuln_data.get("via", [])
        direct_vulns = [v for v in via_entries if isinstance(v, dict)]
        if not direct_vulns:
            continue

        severity = vuln_data.get("severity", "unknown")
        # Normalize npm severity names
        if severity == "moderate":
            severity = "medium"

        is_new = pkg_name in new_deps
        fix_available = vuln_data.get("fixAvailable", False)

        for vuln in direct_vulns:
            findings.append(
                AuditFinding(
                    package=pkg_name,
                    version="",  # npm audit doesn't always include version per vuln
                    vuln_id=f"npm-{vuln.get('source', 'unknown')}",
                    severity=severity,
                    description=vuln.get("title", ""),
                    fix_versions=["fix available"] if fix_available else [],
                    is_new_dep=is_new,
                )
            )

    return findings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/security/test_npm_audit.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff format src/agent_harness/security/npm_audit.py tests/security/test_npm_audit.py
git add src/agent_harness/security/npm_audit.py tests/security/test_npm_audit.py
git commit -m "feat: add npm-audit runner for security audit"
```

### Task 7: Security Config (ignore list from .agent-harness.yml)

**Files:**
- Create: `src/agent_harness/security/config.py`
- Test: `tests/security/test_security_config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/security/test_security_config.py`:

```python
from datetime import date

from agent_harness.security.config import load_security_config, SecurityConfig


def test_empty_config():
    config = load_security_config({})
    assert config.ignored_cves == set()
    assert config.base_branch == "origin/main"


def test_ignore_list():
    config = load_security_config({
        "security": {
            "ignore": [
                {"id": "CVE-2025-1111", "reason": "No fix", "expires": "2026-12-31"},
                {"id": "CVE-2025-2222", "reason": "False positive"},
            ]
        }
    })
    assert config.ignored_cves == {"CVE-2025-1111", "CVE-2025-2222"}


def test_expired_ignore_excluded(monkeypatch):
    """Expired CVE ignores should not be in the set."""
    monkeypatch.setattr(
        "agent_harness.security.config._today", lambda: date(2026, 4, 1)
    )
    config = load_security_config({
        "security": {
            "ignore": [
                {"id": "CVE-2025-1111", "reason": "No fix", "expires": "2026-03-01"},
                {"id": "CVE-2025-2222", "reason": "Still valid", "expires": "2026-12-31"},
            ]
        }
    })
    assert config.ignored_cves == {"CVE-2025-2222"}


def test_custom_base_branch():
    config = load_security_config({
        "security": {"base_branch": "origin/develop"}
    })
    assert config.base_branch == "origin/develop"


def test_no_expiry_never_expires():
    config = load_security_config({
        "security": {
            "ignore": [
                {"id": "CVE-2025-9999", "reason": "Permanent ignore"},
            ]
        }
    })
    assert config.ignored_cves == {"CVE-2025-9999"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/security/test_security_config.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement security config**

Create `src/agent_harness/security/config.py`:

```python
"""Security audit configuration from .agent-harness.yml."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


def _today() -> date:
    return date.today()


@dataclass
class SecurityConfig:
    """Parsed security configuration."""

    ignored_cves: set[str] = field(default_factory=set)
    base_branch: str = "origin/main"


def load_security_config(config: dict) -> SecurityConfig:
    """Extract security settings from the harness config dict."""
    security = config.get("security", {})
    if not isinstance(security, dict):
        return SecurityConfig()

    base_branch = security.get("base_branch", "origin/main")

    ignored_cves: set[str] = set()
    today = _today()

    for entry in security.get("ignore", []):
        if not isinstance(entry, dict):
            continue
        cve_id = entry.get("id", "")
        expires_str = entry.get("expires")

        if expires_str:
            try:
                expires = date.fromisoformat(expires_str)
                if expires < today:
                    continue  # Expired — don't ignore
            except ValueError:
                pass  # Bad date format — include anyway

        ignored_cves.add(cve_id)

    return SecurityConfig(ignored_cves=ignored_cves, base_branch=base_branch)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/security/test_security_config.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff format src/agent_harness/security/config.py tests/security/test_security_config.py
git add src/agent_harness/security/config.py tests/security/test_security_config.py
git commit -m "feat: add security config with CVE ignore list and expiry"
```

### Task 8: Security Audit Orchestrator

**Files:**
- Create: `src/agent_harness/security/audit.py`
- Test: `tests/security/test_audit.py`

- [ ] **Step 1: Write failing tests**

Create `tests/security/test_audit.py`:

```python
from unittest.mock import patch

from agent_harness.security.audit import run_security_audit
from agent_harness.security.models import AuditFinding, SecurityReport


def test_audit_python_project(tmp_path):
    """Python project with pip-audit findings."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["requests"]\n'
    )

    mock_findings = [
        AuditFinding(
            package="requests",
            version="2.25.0",
            vuln_id="CVE-2026-1234",
            severity="high",
            description="bad",
            fix_versions=["2.25.1"],
            is_new_dep=False,
        ),
    ]

    with (
        patch(
            "agent_harness.security.audit.run_pip_audit", return_value='{"dependencies":[],"fixes":[]}'
        ),
        patch(
            "agent_harness.security.audit.parse_pip_audit_output", return_value=mock_findings
        ),
        patch(
            "agent_harness.security.audit.detect_new_deps", return_value=set()
        ),
    ):
        report = run_security_audit(
            tmp_path, stacks={"python"}, config={}
        )

    assert isinstance(report, SecurityReport)
    assert len(report.findings) == 1


def test_audit_no_stacks(tmp_path):
    """No stacks detected — empty report."""
    report = run_security_audit(tmp_path, stacks=set(), config={})
    assert isinstance(report, SecurityReport)
    assert report.findings == []


def test_audit_tool_unavailable(tmp_path):
    """Audit tool not installed — empty report with no crash."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["requests"]\n'
    )

    with (
        patch("agent_harness.security.audit.run_pip_audit", return_value=None),
        patch("agent_harness.security.audit.detect_new_deps", return_value=set()),
    ):
        report = run_security_audit(
            tmp_path, stacks={"python"}, config={}
        )

    assert report.findings == []


def test_audit_applies_ignores(tmp_path):
    """Ignored CVEs should be reflected in the report."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["requests"]\n'
    )

    mock_findings = [
        AuditFinding("requests", "2.25.0", "CVE-2026-1234", "high", "bad", ["2.25.1"], is_new_dep=True),
    ]

    config = {"security": {"ignore": [{"id": "CVE-2026-1234", "reason": "known"}]}}

    with (
        patch("agent_harness.security.audit.run_pip_audit", return_value='{"dependencies":[],"fixes":[]}'),
        patch("agent_harness.security.audit.parse_pip_audit_output", return_value=mock_findings),
        patch("agent_harness.security.audit.detect_new_deps", return_value={"requests"}),
    ):
        report = run_security_audit(tmp_path, stacks={"python"}, config=config)

    assert report.has_failures is False
    assert report.ignored_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/security/test_audit.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement orchestrator**

Create `src/agent_harness/security/audit.py`:

```python
"""Security audit orchestrator — detect stacks, run tools, apply policy."""

from __future__ import annotations

from pathlib import Path

from agent_harness.security.config import load_security_config
from agent_harness.security.dep_diff import detect_new_deps
from agent_harness.security.models import AuditFinding, SecurityReport
from agent_harness.security.npm_audit import parse_npm_audit_output, run_npm_audit
from agent_harness.security.pip_audit import parse_pip_audit_output, run_pip_audit


def run_security_audit(
    project_dir: Path,
    stacks: set[str],
    config: dict,
) -> SecurityReport:
    """Run security audit for all detected stacks."""
    sec_config = load_security_config(config)
    all_findings: list[AuditFinding] = []

    # Detect new dependencies
    new_deps = detect_new_deps(project_dir, base_branch=sec_config.base_branch)

    # Python audit
    if "python" in stacks:
        output = run_pip_audit(project_dir)
        if output is not None:
            all_findings.extend(parse_pip_audit_output(output, new_deps))

    # JavaScript audit
    if "javascript" in stacks:
        output = run_npm_audit(project_dir)
        if output is not None:
            all_findings.extend(parse_npm_audit_output(output, new_deps))

    return SecurityReport(
        findings=all_findings,
        ignored_ids=sec_config.ignored_cves,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/security/test_audit.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff format src/agent_harness/security/audit.py tests/security/test_audit.py
git add src/agent_harness/security/audit.py tests/security/test_audit.py
git commit -m "feat: add security audit orchestrator"
```

### Task 9: CLI Command + Display

**Files:**
- Modify: `src/agent_harness/cli.py:1-122`
- Create: `src/agent_harness/security/display.py`
- Test: `tests/security/test_display.py`
- Test: `tests/test_cli.py` (add security-audit CLI test)

- [ ] **Step 1: Write failing tests for display**

Create `tests/security/test_display.py`:

```python
from agent_harness.security.display import format_report
from agent_harness.security.models import AuditFinding, Classification, SecurityReport


def test_format_empty_report():
    report = SecurityReport(findings=[], ignored_ids=set())
    lines = format_report(report)
    assert any("no vulnerabilities" in line.lower() for line in lines)


def test_format_report_with_fail():
    findings = [
        AuditFinding("evil", "1.0", "CVE-1", "high", "RCE", ["1.1"], is_new_dep=True),
    ]
    report = SecurityReport(findings=findings, ignored_ids=set())
    lines = format_report(report)
    output = "\n".join(lines)
    assert "FAIL" in output
    assert "evil" in output
    assert "CVE-1" in output


def test_format_report_with_warn():
    findings = [
        AuditFinding("old", "1.0", "CVE-2", "high", "XSS", ["1.1"], is_new_dep=False),
    ]
    report = SecurityReport(findings=findings, ignored_ids=set())
    lines = format_report(report)
    output = "\n".join(lines)
    assert "WARN" in output
    assert "old" in output


def test_format_report_with_ignored():
    findings = [
        AuditFinding("pkg", "1.0", "CVE-3", "high", "bad", ["1.1"], is_new_dep=True),
    ]
    report = SecurityReport(findings=findings, ignored_ids={"CVE-3"})
    lines = format_report(report)
    output = "\n".join(lines)
    assert "ignored" in output.lower()


def test_format_summary_line():
    findings = [
        AuditFinding("a", "1.0", "CVE-1", "high", "x", ["1.1"], is_new_dep=True),
        AuditFinding("b", "1.0", "CVE-2", "low", "y", ["1.1"], is_new_dep=False),
    ]
    report = SecurityReport(findings=findings, ignored_ids=set())
    lines = format_report(report)
    summary = lines[-1]
    assert "1" in summary  # 1 fail
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/security/test_display.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement display**

Create `src/agent_harness/security/display.py`:

```python
"""Security audit display formatting."""

from __future__ import annotations

from agent_harness.security.models import Classification, SecurityReport


def format_report(report: SecurityReport) -> list[str]:
    """Format a SecurityReport as human-readable lines."""
    lines: list[str] = []

    if not report.findings:
        lines.append("  No vulnerabilities found.")
        return lines

    # Group by classification
    fails: list[str] = []
    warns: list[str] = []
    ignored_lines: list[str] = []

    for finding in report.findings:
        if finding.vuln_id in report.ignored_ids:
            ignored_lines.append(
                f"  SKIP  {finding.package} {finding.vuln_id} (ignored)"
            )
            continue

        classification = finding.classify()
        fix_info = f" → fix: {', '.join(finding.fix_versions)}" if finding.fix_versions else " (no fix)"
        new_tag = " [NEW]" if finding.is_new_dep else ""
        line = (
            f"  {finding.package}@{finding.version}{new_tag} "
            f"{finding.vuln_id} ({finding.severity}){fix_info}"
        )

        if classification == Classification.FAIL:
            fails.append(f"  FAIL  {line.strip()}")
        else:
            warns.append(f"  WARN  {line.strip()}")

    for line in fails:
        lines.append(line)
    for line in warns:
        lines.append(line)
    for line in ignored_lines:
        lines.append(line)

    # Summary
    summary_parts = []
    if report.fail_count:
        summary_parts.append(f"{report.fail_count} blocked")
    if report.warn_count:
        summary_parts.append(f"{report.warn_count} warnings")
    if report.ignored_count:
        summary_parts.append(f"{report.ignored_count} ignored")
    lines.append(f"\n  {', '.join(summary_parts)}")

    return lines
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/security/test_display.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Add CLI command**

Add to `src/agent_harness/cli.py` after the `init` command:

```python
@cli.command("security-audit")
@click.option(
    "--base-branch",
    default=None,
    help="Base branch for dep diff (default: from config or origin/main)",
)
def security_audit(base_branch):
    """Audit dependencies for known vulnerabilities.

    Detects newly added packages and flags High/Critical CVEs that have
    fixes available. Existing dependencies are warned but don't block.

    Configure ignores in .agent-harness.yml under 'security.ignore'.
    """
    from agent_harness.config import load_config
    from agent_harness.security.audit import run_security_audit
    from agent_harness.security.display import format_report

    cwd = Path.cwd()
    config = load_config(cwd)

    if base_branch:
        config.setdefault("security", {})["base_branch"] = base_branch

    stacks = config.get("stacks", set())
    click.echo("Running security audit...")

    report = run_security_audit(cwd, stacks=stacks, config=config)

    for line in format_report(report):
        click.echo(line)

    if report.has_failures:
        raise SystemExit(1)
```

- [ ] **Step 6: Write CLI integration test**

Add to `tests/test_cli.py`:

```python
def test_security_audit_command_exists():
    """security-audit command is registered."""
    from click.testing import CliRunner
    from agent_harness.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["security-audit", "--help"])
    assert result.exit_code == 0
    assert "security" in result.output.lower()
```

- [ ] **Step 7: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 8: Lint and commit**

```bash
uv run ruff format src/agent_harness/security/display.py tests/security/test_display.py src/agent_harness/cli.py tests/test_cli.py
git add src/agent_harness/security/display.py tests/security/test_display.py src/agent_harness/cli.py tests/test_cli.py
git commit -m "feat: add security-audit CLI command with display formatting"
```

### Task 10: Init Check for Audit Tools + Template Updates

**Files:**
- Create: `src/agent_harness/presets/python/security_setup.py`
- Create: `src/agent_harness/presets/javascript/security_setup.py`
- Modify: `src/agent_harness/presets/python/__init__.py:29-41`
- Modify: `src/agent_harness/presets/javascript/__init__.py`
- Modify: `src/agent_harness/init/templates.py`
- Test: `tests/presets/python/test_security_setup.py`

- [ ] **Step 1: Write failing tests for Python security setup check**

Create `tests/presets/python/test_security_setup.py`:

```python
from pathlib import Path

from agent_harness.presets.python.security_setup import check_python_security_setup


def test_no_pyproject(tmp_path: Path):
    issues = check_python_security_setup(tmp_path)
    assert issues == []


def test_pip_audit_in_dev_deps(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("""\
[project]
name = "test"

[dependency-groups]
dev = ["pip-audit>=2.7", "pytest"]
""")
    issues = check_python_security_setup(tmp_path)
    assert issues == []


def test_pip_audit_missing(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("""\
[project]
name = "test"

[dependency-groups]
dev = ["pytest", "ruff"]
""")
    issues = check_python_security_setup(tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "recommendation"
    assert "pip-audit" in issues[0].message
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/presets/python/test_security_setup.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement Python security setup check**

Create `src/agent_harness/presets/python/security_setup.py`:

```python
"""Python security setup check — verify pip-audit is available."""

from __future__ import annotations

from pathlib import Path

from agent_harness.setup_check import SetupIssue

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]


def check_python_security_setup(project_dir: Path) -> list[SetupIssue]:
    """Check that pip-audit is in dev dependencies."""
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return []

    data = tomllib.loads(pyproject_path.read_text())

    # Check all places where pip-audit could be declared
    all_dev_deps: list[str] = []

    # [dependency-groups]
    for group_deps in data.get("dependency-groups", {}).values():
        for dep in group_deps:
            if isinstance(dep, str):
                all_dev_deps.append(dep.lower())

    # [project.optional-dependencies]
    for group_deps in data.get("project", {}).get("optional-dependencies", {}).values():
        for dep in group_deps:
            all_dev_deps.append(dep.lower())

    has_pip_audit = any("pip-audit" in dep for dep in all_dev_deps)

    if not has_pip_audit:
        return [
            SetupIssue(
                file="pyproject.toml",
                message="pip-audit not in dev dependencies — add for security auditing",
                severity="recommendation",
            )
        ]

    return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/presets/python/test_security_setup.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Wire into PythonPreset.run_setup()**

In `src/agent_harness/presets/python/__init__.py`, update `run_setup()`:

```python
def run_setup(self, project_dir: Path, config: dict) -> list[SetupIssue]:
    from .security_setup import check_python_security_setup
    from .setup_check import check_python_setup

    issues = check_python_setup(project_dir)
    issues.extend(check_python_security_setup(project_dir))
    return issues
```

- [ ] **Step 6: Update Makefile templates**

In `src/agent_harness/init/templates.py`, update `MAKEFILE_PYTHON` to add security-audit to the `check` target:

```python
MAKEFILE_PYTHON = """\
.PHONY: lint fix test check coverage-diff security-audit bootstrap

lint:
\tagent-harness lint

fix:
\tagent-harness fix

test:
\t{test_command}

coverage-diff:
\t@uv run diff-cover coverage.xml --compare-branch=origin/main --fail-under=95

security-audit:
\tagent-harness security-audit

check: lint test coverage-diff security-audit

bootstrap: ## First-time setup after clone
\tuv sync
\tagent-harness init --apply
\t@if command -v prek >/dev/null; then prek install; \\
\telif command -v pre-commit >/dev/null; then pre-commit install; \\
\telse echo "Install prek (brew install prek) or pre-commit for git hooks"; fi
\t@echo "Done. Run 'make check' to verify."
"""
```

Also update `MAKEFILE` (generic) to add the security-audit target:

```python
MAKEFILE = """\
.PHONY: lint fix test check security-audit bootstrap

lint:
\tagent-harness lint

fix:
\tagent-harness fix

test:
\t{test_command}

security-audit:
\tagent-harness security-audit

check: lint test security-audit

bootstrap: ## First-time setup after clone
\t{install_deps}
\tagent-harness init --apply
\t@if command -v prek >/dev/null; then prek install; \\
\telif command -v pre-commit >/dev/null; then pre-commit install; \\
\telse echo "Install prek (brew install prek) or pre-commit for git hooks"; fi
\t@echo "Done. Run 'make check' to verify."
"""
```

- [ ] **Step 7: Update CLAUDEMD template**

In `src/agent_harness/init/templates.py`, update `CLAUDEMD`:

```python
CLAUDEMD = """\
# {project_name}

## Dev Commands

```bash
make lint             # agent-harness lint (runs all checks, safe anytime)
make fix              # auto-fix formatting, then lint
make test             # run tests{coverage_note}
make security-audit   # check deps for known vulnerabilities
make check            # full gate: lint + test{coverage_diff_note} + security-audit
make bootstrap        # first-time setup: deps + harness config + pre-commit hooks
```

## Workflow

Pre-commit hooks run `agent-harness fix` and `agent-harness lint` automatically on every commit.
Before declaring work done, always run `make check` — it's the full quality gate.{coverage_diff_workflow}

## Never

- Never truncate lint/test output with `| tail` or `| head` — output is already optimized
- Never skip `make check` before declaring a task complete
"""
```

- [ ] **Step 8: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests pass (some init tests may need updating if they check template content)

- [ ] **Step 9: Lint and commit**

```bash
uv run ruff format src/agent_harness/presets/python/security_setup.py tests/presets/python/test_security_setup.py src/agent_harness/presets/python/__init__.py src/agent_harness/init/templates.py
git add src/agent_harness/presets/python/security_setup.py tests/presets/python/test_security_setup.py src/agent_harness/presets/python/__init__.py src/agent_harness/presets/javascript/__init__.py src/agent_harness/init/templates.py
git commit -m "feat: add security audit init checks and update templates"
```

### Task 11: Update SKILL.md and CLAUDE.md with Security Audit

**Files:**
- Modify: `skills/agent-harness/SKILL.md`
- Modify: `CLAUDE.md` (project root)

- [ ] **Step 1: Update SKILL.md**

Add security-audit to the Commands section in `skills/agent-harness/SKILL.md`:

```markdown
## Commands

- `agent-harness init` — Diagnose harness setup (report mode)
- `agent-harness init --apply` — Apply auto-fixes and create missing config files
- `agent-harness lint` — Run all harness checks (fast, pass/fail, blocks commits)
- `agent-harness fix` — Auto-fix what's fixable (ruff format/check --fix), then lint
- `agent-harness detect` — Show detected stacks and subprojects
- `agent-harness security-audit` — Audit deps for known vulnerabilities (requires network)
```

Update the lint mode description to mention security-audit:

```markdown
### Three modes, clean separation

- **lint** — Fast enforcement every commit. "Is this gate broken?" Checks: ruff, ty, conftest policies, yamllint, file length, gitignore tracked files, pre-commit hooks.
- **init** — On-demand diagnostic. "Is this gate configured well?" Checks config quality, gitignore completeness, CLAUDE.md workflow, missing tools.
- **security-audit** — Dep vulnerability scan. "Are any new deps dangerous?" Only blocks on new + High/Critical + fix available. Runs in `make check`, not in lint.
```

- [ ] **Step 2: Update project CLAUDE.md**

Add `make security-audit` to the Dev Commands in the project's root `CLAUDE.md`:

```markdown
## Dev Commands

```bash
make lint             # agent-harness lint (runs all checks)
make fix              # agent-harness fix (auto-fix, then lint)
make test             # pytest + conftest verify (all tests)
make security-audit   # check deps for known vulnerabilities
```
```

- [ ] **Step 3: Commit**

```bash
git add skills/agent-harness/SKILL.md CLAUDE.md
git commit -m "docs: add security-audit to skill and project docs"
```

### Task 12: Config Documentation in .agent-harness.yml Template

**Files:**
- Modify: `src/agent_harness/init/templates.py` (HARNESS_YML template)

- [ ] **Step 1: Add security config section to HARNESS_YML template**

Update the `HARNESS_YML` template in `src/agent_harness/init/templates.py`:

```python
HARNESS_YML = """\
# AI Harness configuration
# Detected stacks: {stacks}
stacks: [{stacks_list}]

# exclude:
#   - _archive/
#   - vendor/

# python:
#   coverage_threshold: 95
#   line_length: 120

# javascript:
#   coverage_threshold: 80

# docker:
#   own_image_prefix: "ghcr.io/myorg/"

# security:
#   base_branch: origin/main
#   ignore:
#     - id: CVE-2025-XXXX
#       reason: "No fix available, transitive dep"
#       expires: 2026-06-01
"""
```

- [ ] **Step 2: Lint and commit**

```bash
uv run ruff format src/agent_harness/init/templates.py
git add src/agent_harness/init/templates.py
git commit -m "docs: add security config section to harness yml template"
```

---

## Verification

### Final Integration Test

After all tasks are complete:

- [ ] **Step 1:** Run full test suite: `uv run pytest tests/ -v`
- [ ] **Step 2:** Run lint: `agent-harness lint`
- [ ] **Step 3:** Run init on this project: `agent-harness init`
- [ ] **Step 4:** Run security-audit on this project: `agent-harness security-audit`
- [ ] **Step 5:** Install globally: `uv tool install -e .`
- [ ] **Step 6:** Push: `git push`

### Known Limitations (Future Work)

1. **pip-audit doesn't report severity** — findings default to "unknown" which means they never FAIL. A future enhancement should query OSV API for CVSS scores.
2. **npm audit --json format varies** between npm versions — the parser handles v8+ format. Older npm may need adaptation.
3. **Monorepo support** — security-audit currently runs on cwd only, not auto-discovered subprojects. Add `security_audit_all()` orchestrator if needed.
4. **Severity lookup** — Consider adding OSV API integration to get severity for pip-audit findings, or accept `--severity-override` in config.
