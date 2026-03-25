"""Tests for run_conftest_diagnostic in conftest.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_harness.conftest import DiagnosticResult, run_conftest_diagnostic


def test_diagnostic_missing_file(tmp_path):
    """Target file doesn't exist — returns passed=True with empty lists."""
    result = run_conftest_diagnostic(
        name="test",
        project_dir=tmp_path,
        target_file="nonexistent.yaml",
        policy_subdir="universal",
    )
    assert result.passed is True
    assert result.critical == []
    assert result.recommendations == []
    assert result.name == "test"
    assert result.target_file == "nonexistent.yaml"


def test_diagnostic_parses_json(tmp_path):
    """Mock subprocess returning known JSON — verifies critical/recommendations parsed correctly."""
    target = tmp_path / "docker-compose.yml"
    target.write_text("version: '3'\n")

    conftest_json = json.dumps([
        {
            "filename": str(target),
            "namespace": "main",
            "successes": 1,
            "failures": [{"msg": "deny message one"}, {"msg": "deny message two"}],
            "warnings": [{"msg": "warn message one"}],
        }
    ])

    mock_result = MagicMock()
    mock_result.stdout = conftest_json
    mock_result.returncode = 1

    with patch("agent_harness.conftest._resolve_tool", return_value="/usr/bin/conftest"), \
         patch("agent_harness.conftest.subprocess.run", return_value=mock_result):
        result = run_conftest_diagnostic(
            name="test",
            project_dir=tmp_path,
            target_file="docker-compose.yml",
            policy_subdir="docker",
        )

    assert result.passed is False
    assert result.critical == ["deny message one", "deny message two"]
    assert result.recommendations == ["warn message one"]


def test_diagnostic_conftest_not_found(tmp_path):
    """_resolve_tool returns None — single critical message about conftest not installed."""
    target = tmp_path / "Dockerfile"
    target.write_text("FROM python:3.12\n")

    with patch("agent_harness.conftest._resolve_tool", return_value=None):
        result = run_conftest_diagnostic(
            name="test",
            project_dir=tmp_path,
            target_file="Dockerfile",
            policy_subdir="docker",
        )

    assert result.passed is False
    assert len(result.critical) == 1
    assert "conftest" in result.critical[0].lower()
    assert "not found" in result.critical[0].lower()
    assert result.recommendations == []


def test_diagnostic_invalid_json(tmp_path):
    """Subprocess returns non-JSON output — single critical message about parse error."""
    target = tmp_path / "Dockerfile"
    target.write_text("FROM python:3.12\n")

    mock_result = MagicMock()
    mock_result.stdout = "this is not json at all"
    mock_result.returncode = 1

    with patch("agent_harness.conftest._resolve_tool", return_value="/usr/bin/conftest"), \
         patch("agent_harness.conftest.subprocess.run", return_value=mock_result):
        result = run_conftest_diagnostic(
            name="test",
            project_dir=tmp_path,
            target_file="Dockerfile",
            policy_subdir="docker",
        )

    assert result.passed is False
    assert len(result.critical) == 1
    assert "json" in result.critical[0].lower()
    assert result.recommendations == []


def test_diagnostic_with_data(tmp_path):
    """Data dict creates temp file and passes --data flag to conftest."""
    target = tmp_path / "package.json"
    target.write_text('{"name": "test"}\n')

    mock_result = MagicMock()
    mock_result.stdout = json.dumps([
        {"filename": str(target), "namespace": "main", "successes": 1, "failures": [], "warnings": []}
    ])
    mock_result.returncode = 0

    captured_cmd = []

    def capture_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return mock_result

    extra_data = {"key": "value", "num": 42}

    with patch("agent_harness.conftest._resolve_tool", return_value="/usr/bin/conftest"), \
         patch("agent_harness.conftest.subprocess.run", side_effect=capture_run):
        result = run_conftest_diagnostic(
            name="test",
            project_dir=tmp_path,
            target_file="package.json",
            policy_subdir="javascript",
            data=extra_data,
        )

    assert result.passed is True
    assert result.critical == []
    assert "--data" in captured_cmd
    data_idx = captured_cmd.index("--data")
    data_file = captured_cmd[data_idx + 1]
    # The temp file should have been cleaned up but we can verify the flag was passed
    assert data_file.endswith(".json")
