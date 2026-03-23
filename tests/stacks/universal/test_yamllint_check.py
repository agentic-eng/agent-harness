from agent_harness.stacks.universal.yamllint_check import run_yamllint


def test_yamllint_no_yaml_files(tmp_path):
    """Skip gracefully when no YAML files are tracked."""
    result = run_yamllint(tmp_path)
    assert result.passed


def test_yamllint_skips_lock_files(tmp_path, monkeypatch):
    """Lock files should be excluded even if git-tracked."""
    import subprocess

    def mock_run(cmd, **kwargs):
        if "ls-files" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="pnpm-lock.yaml\n", stderr="")
        return subprocess.run(cmd, **kwargs)

    monkeypatch.setattr("agent_harness.stacks.universal.yamllint_check.subprocess.run", mock_run)
    result = run_yamllint(tmp_path, exclude_patterns=["*-lock.*", "*.lock"])
    assert result.passed
    assert "skipping" in result.output.lower() or "No YAML" in result.output
