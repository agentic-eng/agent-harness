from agent_harness.stacks.docker.conftest_compose_check import run_conftest_compose


def test_conftest_compose_no_file(tmp_path):
    """Skip gracefully when no docker-compose.prod.yml exists."""
    result = run_conftest_compose(tmp_path)
    assert result.passed
