from agent_harness.stacks.docker.hadolint_check import run_hadolint


def test_hadolint_no_dockerfile(tmp_path):
    """Skip gracefully when no Dockerfile exists."""
    result = run_hadolint(tmp_path)
    assert result.passed
