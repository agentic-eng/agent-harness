from agent_harness.stacks.javascript.detect import detect_javascript


def test_detect_package_json(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}')
    assert detect_javascript(tmp_path)


def test_detect_tsconfig(tmp_path):
    (tmp_path / "tsconfig.json").write_text('{}')
    assert detect_javascript(tmp_path)


def test_detect_none(tmp_path):
    assert not detect_javascript(tmp_path)


def test_detect_python_only(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    assert not detect_javascript(tmp_path)
