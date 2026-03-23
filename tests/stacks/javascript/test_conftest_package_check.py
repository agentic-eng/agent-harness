from agent_harness.stacks.javascript.conftest_package_check import run_conftest_package


def test_skips_when_no_package_json(tmp_path):
    result = run_conftest_package(tmp_path)
    assert result.passed
    assert "Skipping" in result.output
