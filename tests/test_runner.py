from ai_harness.runner import run_check


def test_run_check_success():
    result = run_check("echo", ["echo", "hello"])
    assert result.passed
    assert result.name == "echo"


def test_run_check_failure():
    result = run_check("failing", ["false"])
    assert not result.passed


def test_run_check_missing_tool():
    result = run_check("nonexistent", ["nonexistent-tool-xyz-123"])
    assert not result.passed
    assert "not found" in result.error.lower()
