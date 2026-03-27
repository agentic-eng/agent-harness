import subprocess

from agent_harness.presets.universal.precommit_check import run_precommit_check


def _init_git(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)


def test_no_config_passes(tmp_path):
    """No .pre-commit-config.yaml -> pass (nothing to check)."""
    _init_git(tmp_path)
    result = run_precommit_check(tmp_path)
    assert result.passed


def test_config_without_hook_fails(tmp_path):
    """Config exists but hook not installed -> fail."""
    _init_git(tmp_path)
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n")
    result = run_precommit_check(tmp_path)
    assert not result.passed
    assert "not installed" in result.error
    assert "prek install" in result.error


def test_config_with_hook_passes(tmp_path):
    """Config exists and hook installed -> pass."""
    _init_git(tmp_path)
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n")
    hook = tmp_path / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\npre-commit run\n")
    result = run_precommit_check(tmp_path)
    assert result.passed


def test_monorepo_checks_git_root(tmp_path):
    """In monorepo, checks git root for config and hooks."""
    _init_git(tmp_path)
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n")
    subproject = tmp_path / "services" / "api"
    subproject.mkdir(parents=True)

    # No hook installed at root -> fail even from subproject
    result = run_precommit_check(subproject, git_root=tmp_path)
    assert not result.passed

    # Install hook at root -> pass from subproject
    hook = tmp_path / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\npre-commit run\n")
    result = run_precommit_check(subproject, git_root=tmp_path)
    assert result.passed
