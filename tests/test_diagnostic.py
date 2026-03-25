"""Tests for diagnostic display module."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_harness.conftest import DiagnosticResult
from agent_harness.init.diagnostic import display_diagnostics, display_summary
from agent_harness.preset import ToolInfo


def capture_output(fn, *args, **kwargs):
    output = StringIO()
    with patch("click.echo", side_effect=lambda x="", **kw: output.write(str(x) + "\n")):
        result = fn(*args, **kwargs)
    return output.getvalue(), result


def test_display_diagnostics_critical():
    diag = DiagnosticResult(
        name="pytest_check",
        target_file="pyproject.toml",
        critical=["addopts missing --strict-markers"],
        passed=False,
    )
    text, (critical_count, rec_count) = capture_output(
        display_diagnostics, "python", [diag], [], Path("/tmp")
    )
    assert "✗" in text
    assert "pyproject.toml" in text
    assert "addopts missing --strict-markers" in text
    assert "critical" in text
    assert critical_count == 1
    assert rec_count == 0


def test_display_diagnostics_recommendations():
    diag = DiagnosticResult(
        name="ruff_check",
        target_file="pyproject.toml",
        recommendations=['ruff output-format is "full"'],
        passed=True,
    )
    text, (critical_count, rec_count) = capture_output(
        display_diagnostics, "python", [diag], [], Path("/tmp")
    )
    assert "~" in text
    assert "pyproject.toml" in text
    assert 'ruff output-format is "full"' in text
    assert "recommendation" in text
    assert critical_count == 0
    assert rec_count == 1


def test_display_diagnostics_tools_available():
    tool = ToolInfo(
        name="ruff",
        description="Python linter",
        binary="ruff",
        install_hint="pip install ruff",
    )
    with patch("agent_harness.init.diagnostic.tool_available", return_value=True):
        text, (critical_count, rec_count) = capture_output(
            display_diagnostics, "python", [], [tool], Path("/tmp")
        )
    assert "✓" in text
    assert "ruff installed" in text
    assert critical_count == 0
    assert rec_count == 0


def test_display_diagnostics_tools_missing():
    tool = ToolInfo(
        name="ruff",
        description="Python linter",
        binary="ruff",
        install_hint="pip install ruff",
    )
    with patch("agent_harness.init.diagnostic.tool_available", return_value=False):
        text, (critical_count, rec_count) = capture_output(
            display_diagnostics, "python", [], [tool], Path("/tmp")
        )
    assert "✗" in text
    assert "ruff not installed" in text
    assert "pip install ruff" in text
    assert critical_count == 1
    assert rec_count == 0


def test_display_summary_mixed():
    text, _ = capture_output(display_summary, 2, 3, 1)
    assert "2 critical" in text
    assert "3 recommendations" in text
    assert "1 file to create" in text


def test_display_summary_all_passed():
    text, _ = capture_output(display_summary, 0, 0, 0)
    assert "All checks passed" in text
