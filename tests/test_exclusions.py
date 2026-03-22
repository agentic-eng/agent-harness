from agent_harness.exclusions import get_excluded_patterns, is_excluded


def test_default_exclusions_include_lock_files():
    patterns = get_excluded_patterns([])
    assert "*.lock" in patterns
    assert "package-lock.json" in patterns


def test_config_exclusions_extend_defaults():
    patterns = get_excluded_patterns(["vendor/", "generated/"])
    assert "*.lock" in patterns
    assert "vendor/" in patterns


def test_is_excluded_matches_lock_file():
    patterns = get_excluded_patterns([])
    assert is_excluded("pnpm-lock.yaml", patterns)
    assert is_excluded("package-lock.json", patterns)
    assert not is_excluded("src/main.py", patterns)


def test_is_excluded_matches_directory_prefix():
    patterns = get_excluded_patterns(["_archive/"])
    assert is_excluded("_archive/old/tsconfig.json", patterns)
    assert not is_excluded("src/archive.py", patterns)


def test_is_excluded_matches_glob():
    patterns = get_excluded_patterns([])
    assert is_excluded("poetry.lock", patterns)
    assert is_excluded("yarn.lock", patterns)
    assert is_excluded("Gemfile.lock", patterns)
