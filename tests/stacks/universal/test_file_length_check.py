import subprocess
from agent_harness.stacks.universal.file_length_check import run_file_length


def _init_git(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)


def test_py_file_over_500_fails(tmp_path):
    (tmp_path / "big.py").write_text("x = 1\n" * 501)
    _init_git(tmp_path)
    result = run_file_length(tmp_path)
    assert not result.passed
    assert "big.py" in (result.error or result.output)


def test_astro_file_under_800_passes(tmp_path):
    (tmp_path / "Page.astro").write_text("<div>hi</div>\n" * 750)
    _init_git(tmp_path)
    result = run_file_length(tmp_path)
    assert result.passed


def test_astro_file_over_800_fails(tmp_path):
    (tmp_path / "Page.astro").write_text("<div>hi</div>\n" * 801)
    _init_git(tmp_path)
    result = run_file_length(tmp_path)
    assert not result.passed


def test_custom_thresholds(tmp_path):
    (tmp_path / "small.py").write_text("x = 1\n" * 301)
    _init_git(tmp_path)
    result = run_file_length(tmp_path, max_lines_override={".py": 300})
    assert not result.passed


def test_excluded_files_skipped(tmp_path):
    (tmp_path / "big.py").write_text("x = 1\n" * 501)
    _init_git(tmp_path)
    result = run_file_length(tmp_path, exclude_patterns=["big.py"])
    assert result.passed


def test_unknown_extensions_skipped(tmp_path):
    (tmp_path / "data.csv").write_text("a,b\n" * 10000)
    _init_git(tmp_path)
    result = run_file_length(tmp_path)
    assert result.passed
