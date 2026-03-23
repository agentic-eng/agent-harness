from agent_harness.stacks.universal.conftest_json_check import run_conftest_json


def test_conftest_json_no_files(tmp_path):
    """Skip gracefully when no JSON files are tracked."""
    result = run_conftest_json(tmp_path)
    assert result.passed


def test_conftest_json_skips_jsonc_files(tmp_path, monkeypatch):
    """tsconfig.json and jsconfig.json are JSONC — skip them."""
    import subprocess

    def mock_run(cmd, **kwargs):
        if "ls-files" in cmd:
            return subprocess.CompletedProcess(
                cmd, 0, stdout="tsconfig.json\npackage.json\n", stderr=""
            )
        if "conftest" in cmd and "tsconfig.json" in str(cmd):
            raise AssertionError("Should not parse tsconfig.json")
        return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

    monkeypatch.setattr(
        "agent_harness.stacks.universal.conftest_json_check.subprocess.run", mock_run
    )
    result = run_conftest_json(tmp_path, exclude_patterns=[])
    assert result.passed


def test_conftest_json_skips_excluded_files(tmp_path, monkeypatch):
    """Excluded JSON files should be filtered out."""
    import subprocess

    def mock_run(cmd, **kwargs):
        if "ls-files" in cmd:
            return subprocess.CompletedProcess(
                cmd, 0, stdout="package-lock.json\n", stderr=""
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

    monkeypatch.setattr(
        "agent_harness.stacks.universal.conftest_json_check.subprocess.run", mock_run
    )
    result = run_conftest_json(tmp_path, exclude_patterns=["package-lock.json"])
    assert result.passed
    assert "no JSON" in result.output.lower() or "skipping" in result.output.lower()
