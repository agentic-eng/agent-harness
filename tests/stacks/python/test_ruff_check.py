from agent_harness.stacks.python.ruff_check import run_ruff


def test_ruff_returns_list(tmp_path):
    """run_ruff always returns a list of CheckResult."""
    results = run_ruff(tmp_path)
    assert isinstance(results, list)
    assert len(results) == 2
