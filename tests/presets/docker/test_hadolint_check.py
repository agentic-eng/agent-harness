from agent_harness.presets.docker.hadolint_check import run_hadolint


def test_hadolint_no_dockerfile(tmp_path):
    """Skip gracefully when no Dockerfile exists."""
    results = run_hadolint(tmp_path)
    assert len(results) == 1
    assert results[0].passed
