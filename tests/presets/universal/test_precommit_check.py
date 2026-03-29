import subprocess

import pytest

from agent_harness.presets.universal.precommit_check import run_precommit_check


@pytest.fixture(autouse=True)
def _no_ci_env(monkeypatch):
    """Ensure CI env var is unset so precommit check runs normally in tests."""
    monkeypatch.delenv("CI", raising=False)


def test_no_config_passes(git_repo):
    """No .pre-commit-config.yaml -> pass (nothing to check)."""
    result = run_precommit_check(git_repo)
    assert result.passed


def test_config_without_hook_fails(git_repo):
    """Config exists but hook not installed -> fail."""
    (git_repo / ".pre-commit-config.yaml").write_text("repos: []\n")
    result = run_precommit_check(git_repo)
    assert not result.passed
    assert "not installed" in result.error
    assert "prek install" in result.error


def test_config_with_hook_passes(git_repo):
    """Config exists and hook installed -> pass."""
    (git_repo / ".pre-commit-config.yaml").write_text("repos: []\n")
    hook = git_repo / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\npre-commit run\n")
    result = run_precommit_check(git_repo)
    assert result.passed


def test_monorepo_checks_git_root(git_repo):
    """In monorepo, checks git root for config and hooks."""
    (git_repo / ".pre-commit-config.yaml").write_text("repos: []\n")
    subproject = git_repo / "services" / "api"
    subproject.mkdir(parents=True)

    # No hook installed at root -> fail even from subproject
    result = run_precommit_check(subproject, git_root=git_repo)
    assert not result.passed

    # Install hook at root -> pass from subproject
    hook = git_repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\npre-commit run\n")
    result = run_precommit_check(subproject, git_root=git_repo)
    assert result.passed


def test_custom_hooks_path(git_repo):
    """Respects core.hooksPath when checking for pre-commit hook."""
    (git_repo / ".pre-commit-config.yaml").write_text("repos: []\n")

    # Set custom hooks path
    custom_hooks = git_repo / "custom-hooks"
    custom_hooks.mkdir()
    subprocess.run(
        ["git", "config", "core.hooksPath", str(custom_hooks)],
        cwd=str(git_repo),
        capture_output=True,
    )

    # No hook in custom path -> fail
    result = run_precommit_check(git_repo)
    assert not result.passed

    # Hook in custom path -> pass
    hook = custom_hooks / "pre-commit"
    hook.write_text("#!/bin/sh\npre-commit run\n")
    result = run_precommit_check(git_repo)
    assert result.passed


def test_relative_hooks_path(git_repo):
    """Respects relative core.hooksPath."""
    (git_repo / ".pre-commit-config.yaml").write_text("repos: []\n")

    # Set relative hooks path
    rel_hooks = git_repo / "my-hooks"
    rel_hooks.mkdir()
    subprocess.run(
        ["git", "config", "core.hooksPath", "my-hooks"],
        cwd=str(git_repo),
        capture_output=True,
    )

    # No hook -> fail
    result = run_precommit_check(git_repo)
    assert not result.passed

    # Hook in relative path -> pass
    hook = rel_hooks / "pre-commit"
    hook.write_text("#!/bin/sh\npre-commit run\n")
    result = run_precommit_check(git_repo)
    assert result.passed
