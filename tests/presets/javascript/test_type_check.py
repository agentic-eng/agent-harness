import json
from unittest.mock import patch, MagicMock
from agent_harness.presets.javascript.type_check import run_type_check, detect_framework


def test_detect_astro(tmp_path):
    pkg = {"dependencies": {"astro": "^6.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    assert detect_framework(tmp_path) == "astro"


def test_detect_next(tmp_path):
    pkg = {"dependencies": {"next": "^15.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    assert detect_framework(tmp_path) == "next"


def test_detect_default(tmp_path):
    pkg = {"dependencies": {"express": "^4.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    assert detect_framework(tmp_path) is None


def test_astro_uses_astro_check(tmp_path):
    pkg = {"dependencies": {"astro": "^6.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    with patch(
        "agent_harness.presets.javascript.type_check.shutil.which",
        return_value="/usr/bin/astro",
    ):
        with patch("agent_harness.presets.javascript.type_check.run_check") as mock_run:
            mock_run.return_value = MagicMock(passed=True)
            run_type_check(tmp_path)
            cmd = mock_run.call_args[0][1]
            assert "astro" in cmd and "check" in cmd


def test_fallback_uses_tsc(tmp_path):
    pkg = {"dependencies": {"express": "^4.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    with patch(
        "agent_harness.presets.javascript.type_check.shutil.which",
        return_value="/usr/bin/tsc",
    ):
        with patch("agent_harness.presets.javascript.type_check.run_check") as mock_run:
            mock_run.return_value = MagicMock(passed=True)
            run_type_check(tmp_path)
            cmd = mock_run.call_args[0][1]
            assert "tsc" in cmd
