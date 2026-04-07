"""Tests for the generic skip mechanism in lint.py."""

import subprocess

from agent_harness.lint import _is_skipped, run_lint


def test_exact_match():
    assert _is_skipped("typecheck:tsc", ["typecheck:tsc"])


def test_prefix_match():
    assert _is_skipped("typecheck:tsc", ["typecheck"])
    assert _is_skipped("typecheck:astro", ["typecheck"])


def test_no_match():
    assert not _is_skipped("biome:lint", ["typecheck"])


def test_no_partial_match():
    """'type' should not match 'typecheck:tsc'."""
    assert not _is_skipped("typecheck:tsc", ["type"])


def test_empty_skip_list():
    assert not _is_skipped("typecheck:tsc", [])


def test_multiple_patterns():
    assert _is_skipped("biome:lint", ["typecheck", "biome"])
    assert _is_skipped("typecheck:tsc", ["typecheck", "biome"])
    assert not _is_skipped("yamllint", ["typecheck", "biome"])


def _init_git(path):
    subprocess.run(["git", "init"], cwd=str(path), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(path), capture_output=True)


def test_skip_replaces_result_with_pass(tmp_path):
    """Skipped checks should appear as passed with skip message."""
    (tmp_path / ".agent-harness.yml").write_text("stacks: []\nskip:\n  - yamllint\n")
    (tmp_path / ".gitignore").write_text("")
    _init_git(tmp_path)
    results = run_lint(tmp_path)
    yamllint_results = [r for r in results if r.name == "yamllint"]
    assert len(yamllint_results) == 1
    assert yamllint_results[0].passed
    assert "Skipped" in yamllint_results[0].output
