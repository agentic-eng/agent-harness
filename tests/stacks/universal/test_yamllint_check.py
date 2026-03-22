from agent_harness.stacks.universal.yamllint_check import run_yamllint


def test_yamllint_no_yaml_files(tmp_path):
    """Skip gracefully when no YAML files are tracked."""
    result = run_yamllint(tmp_path)
    assert result.passed
