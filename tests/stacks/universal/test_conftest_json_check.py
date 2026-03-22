from agent_harness.stacks.universal.conftest_json_check import run_conftest_json


def test_conftest_json_no_files(tmp_path):
    """Skip gracefully when no JSON files are tracked."""
    result = run_conftest_json(tmp_path)
    assert result.passed
