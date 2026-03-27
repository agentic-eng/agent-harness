import subprocess
from pathlib import Path

import pytest

from agent_harness.security.dep_diff import (
    detect_new_deps,
    parse_js_deps,
    parse_python_deps,
)


def test_parse_python_deps_project_dependencies():
    content = """\
[project]
dependencies = ["requests>=2.0", "click~=8.0", "rich"]
"""
    assert parse_python_deps(content) == {"requests", "click", "rich"}


def test_parse_python_deps_optional_and_groups():
    content = """\
[project]
dependencies = ["flask"]

[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff"]

[dependency-groups]
test = ["coverage", "pytest-cov"]
"""
    deps = parse_python_deps(content)
    assert deps == {"flask", "pytest", "ruff", "coverage", "pytest-cov"}


def test_parse_python_deps_empty():
    content = "[project]\nname = 'foo'\n"
    assert parse_python_deps(content) == set()


def test_parse_python_deps_extras_in_name():
    """Dep specifier with extras like 'package[extra]>=1.0'."""
    content = """\
[project]
dependencies = ["uvicorn[standard]>=0.20", "boto3"]
"""
    assert parse_python_deps(content) == {"uvicorn", "boto3"}


def test_parse_js_deps():
    content = """\
{
  "dependencies": {"react": "^18.0", "next": "^14.0"},
  "devDependencies": {"jest": "^29.0", "eslint": "^8.0"}
}
"""
    assert parse_js_deps(content) == {"react", "next", "jest", "eslint"}


def test_parse_js_deps_empty():
    content = '{"name": "foo"}'
    assert parse_js_deps(content) == set()


def test_parse_js_deps_peer_and_optional():
    content = """\
{
  "dependencies": {"a": "1"},
  "peerDependencies": {"b": "2"},
  "optionalDependencies": {"c": "3"}
}
"""
    assert parse_js_deps(content) == {"a", "b", "c"}


@pytest.fixture()
def git_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    return tmp_path


def test_detect_new_deps_python(git_repo: Path):
    """New dep added after base branch should be detected."""
    pyproject = git_repo / "pyproject.toml"
    pyproject.write_text('[project]\ndependencies = ["requests"]\n')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(git_repo), capture_output=True
    )
    subprocess.run(["git", "branch", "main"], cwd=str(git_repo), capture_output=True)

    pyproject.write_text('[project]\ndependencies = ["requests", "evil-pkg"]\n')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add dep"], cwd=str(git_repo), capture_output=True
    )

    new_deps = detect_new_deps(git_repo, base_branch="main")
    assert new_deps == {"evil-pkg"}


def test_detect_new_deps_no_base_branch(git_repo: Path):
    """If base branch doesn't exist, all deps are treated as new."""
    pyproject = git_repo / "pyproject.toml"
    pyproject.write_text('[project]\ndependencies = ["requests"]\n')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(git_repo), capture_output=True
    )

    new_deps = detect_new_deps(git_repo, base_branch="main")
    assert new_deps == {"requests"}


def test_detect_new_deps_js(git_repo: Path):
    """New JS dep added after base branch should be detected."""
    pkg = git_repo / "package.json"
    pkg.write_text('{"dependencies": {"react": "^18.0"}}')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(git_repo), capture_output=True
    )
    subprocess.run(["git", "branch", "main"], cwd=str(git_repo), capture_output=True)

    pkg.write_text('{"dependencies": {"react": "^18.0", "evil-js": "^1.0"}}')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add dep"], cwd=str(git_repo), capture_output=True
    )

    new_deps = detect_new_deps(git_repo, base_branch="main")
    assert new_deps == {"evil-js"}


def test_detect_new_deps_upgrade_not_new(git_repo: Path):
    """Upgrading an existing dep version should NOT count as new."""
    pyproject = git_repo / "pyproject.toml"
    pyproject.write_text('[project]\ndependencies = ["requests>=2.0"]\n')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(git_repo), capture_output=True
    )
    subprocess.run(["git", "branch", "main"], cwd=str(git_repo), capture_output=True)

    pyproject.write_text('[project]\ndependencies = ["requests>=3.0"]\n')
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "bump"], cwd=str(git_repo), capture_output=True
    )

    new_deps = detect_new_deps(git_repo, base_branch="main")
    assert new_deps == set()
