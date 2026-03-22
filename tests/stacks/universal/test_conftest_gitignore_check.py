from agent_harness.stacks.universal.conftest_gitignore_check import run_conftest_gitignore


def test_conftest_gitignore_no_file(tmp_path):
    """Skip gracefully when no .gitignore exists."""
    result = run_conftest_gitignore(tmp_path)
    assert result.passed
