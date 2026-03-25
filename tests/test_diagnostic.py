"""Tests for diagnostic display module."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from agent_harness.init.diagnostic import display_setup_issues, display_summary
from agent_harness.preset import ToolInfo
from agent_harness.setup import SetupIssue


def capture_output(fn, *args, **kwargs):
    output = StringIO()
    with patch(
        "click.echo", side_effect=lambda x="", **kw: output.write(str(x) + "\n")
    ):
        result = fn(*args, **kwargs)
    return output.getvalue(), result


def test_display_critical_fixable():
    issue = SetupIssue(
        file="pyproject.toml",
        message="--cov-fail-under not set",
        severity="critical",
        fix=lambda p: None,
    )
    text, (c, r, f) = capture_output(
        display_setup_issues, "python", [issue], [], Path("/tmp")
    )
    assert "✗" in text
    assert "critical" in text
    assert "fixable" in text
    assert c == 1 and r == 0 and f == 1


def test_display_critical_not_fixable():
    issue = SetupIssue(
        file="pyproject.toml",
        message="something wrong",
        severity="critical",
    )
    text, (c, r, f) = capture_output(
        display_setup_issues, "python", [issue], [], Path("/tmp")
    )
    assert "✗" in text
    assert "critical" in text
    assert "fixable" not in text
    assert c == 1 and f == 0


def test_display_recommendation():
    issue = SetupIssue(
        file="pyproject.toml",
        message="--cov-fail-under=50, recommend 90-95%",
        severity="recommendation",
    )
    text, (c, r, f) = capture_output(
        display_setup_issues, "python", [issue], [], Path("/tmp")
    )
    assert "~" in text
    assert "recommendation" in text
    assert c == 0 and r == 1


def test_display_tools_available():
    tool = ToolInfo(
        name="ruff",
        description="linter",
        binary="ruff",
        install_hint="pip install ruff",
    )
    with patch("agent_harness.init.diagnostic.tool_available", return_value=True):
        text, (c, r, f) = capture_output(
            display_setup_issues, "python", [], [tool], Path("/tmp")
        )
    assert "✓" in text
    assert "ruff installed" in text


def test_display_tools_missing():
    tool = ToolInfo(
        name="ruff",
        description="linter",
        binary="ruff",
        install_hint="pip install ruff",
    )
    with patch("agent_harness.init.diagnostic.tool_available", return_value=False):
        text, (c, r, f) = capture_output(
            display_setup_issues, "python", [], [tool], Path("/tmp")
        )
    assert "✗" in text
    assert "ruff not installed" in text
    assert c == 1


def test_display_summary_with_fixable():
    text, _ = capture_output(display_summary, 3, 1, 2, 1)
    assert "3 critical (2 fixable)" in text
    assert "1 recommendation" in text
    assert "1 file to create" in text


def test_display_summary_all_passed():
    text, _ = capture_output(display_summary, 0, 0, 0, 0)
    assert "All checks passed" in text
