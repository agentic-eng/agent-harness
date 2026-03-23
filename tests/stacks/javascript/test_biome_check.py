from unittest.mock import patch, MagicMock, call
from agent_harness.stacks.javascript.biome_check import run_biome


def test_biome_returns_two_results(tmp_path):
    """Biome should run lint and format checks."""
    with patch("agent_harness.stacks.javascript.biome_check.shutil.which", return_value="/usr/bin/biome"):
        with patch("agent_harness.stacks.javascript.biome_check.run_check") as mock_run:
            mock_run.side_effect = [
                MagicMock(passed=True, output="", error="", duration_ms=10, name="biome:lint"),
                MagicMock(passed=True, output="", error="", duration_ms=10, name="biome:format"),
            ]
            results = run_biome(tmp_path)
            assert len(results) == 2
            calls = mock_run.call_args_list
            assert any("lint" in str(c) for c in calls)
            assert any("format" in str(c) for c in calls)


def test_biome_falls_back_to_npx(tmp_path):
    """When biome not in PATH, use npx."""
    with patch("agent_harness.stacks.javascript.biome_check.shutil.which", return_value=None):
        with patch("agent_harness.stacks.javascript.biome_check.run_check") as mock_run:
            mock_run.return_value = MagicMock(passed=True, output="", error="", duration_ms=10, name="biome")
            run_biome(tmp_path)
            calls = mock_run.call_args_list
            assert any("npx" in str(c) for c in calls)
