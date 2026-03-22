from pathlib import Path
from agent_harness.stacks.python.detect import detect_python


def test_detect_python_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    assert detect_python(tmp_path)


def test_detect_python_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text("flask\n")
    assert detect_python(tmp_path)


def test_detect_python_empty(tmp_path):
    assert not detect_python(tmp_path)
