import subprocess
from pathlib import Path

from agent_harness.presets.docker.detect import find_dockerfiles


def _init_git(path):
    subprocess.run(["git", "init"], cwd=str(path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t.com"], cwd=str(path), capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "T"], cwd=str(path), capture_output=True
    )


def test_finds_root_dockerfile(tmp_path):
    _init_git(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    result = find_dockerfiles(tmp_path)
    assert len(result) == 1
    assert result[0].name == "Dockerfile"


def test_finds_nested_dockerfiles(tmp_path):
    _init_git(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    scripts = tmp_path / "scripts" / "autonomy"
    scripts.mkdir(parents=True)
    (scripts / "Dockerfile").write_text("FROM node:22")
    infra = tmp_path / "infrastructure" / "staging"
    infra.mkdir(parents=True)
    (infra / "Dockerfile").write_text("FROM nginx:1.27")
    result = find_dockerfiles(tmp_path)
    assert len(result) == 3


def test_returns_relative_paths(tmp_path):
    _init_git(tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "Dockerfile").write_text("FROM python:3.12")
    result = find_dockerfiles(tmp_path)
    assert result[0] == Path("scripts/Dockerfile")


def test_no_dockerfiles(tmp_path):
    _init_git(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    result = find_dockerfiles(tmp_path)
    assert result == []
