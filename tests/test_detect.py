from agent_harness.detect import detect_stacks


def test_detect_python(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    assert "python" in detect_stacks(tmp_path)


def test_detect_docker(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    assert "docker" in detect_stacks(tmp_path)


def test_detect_compose(tmp_path):
    (tmp_path / "docker-compose.prod.yml").write_text("services:\n  app:\n    image: x")
    assert "docker" in detect_stacks(tmp_path)


def test_detect_multiple(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    stacks = detect_stacks(tmp_path)
    assert "python" in stacks and "docker" in stacks


def test_detect_empty(tmp_path):
    assert detect_stacks(tmp_path) == set()


def test_detect_javascript(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}')
    assert "javascript" in detect_stacks(tmp_path)


def test_detect_javascript_and_docker(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}')
    (tmp_path / "Dockerfile").write_text("FROM node:22")
    stacks = detect_stacks(tmp_path)
    assert "javascript" in stacks and "docker" in stacks


def test_detect_dokploy(tmp_path):
    (tmp_path / "docker-compose.prod.yml").write_text(
        "services:\n  app:\n    networks:\n      - dokploy-network\n"
    )
    assert "dokploy" in detect_stacks(tmp_path)


def test_detect_dokploy_not_detected_without_network(tmp_path):
    (tmp_path / "docker-compose.prod.yml").write_text(
        "services:\n  app:\n    image: myapp:latest\n"
    )
    assert "dokploy" not in detect_stacks(tmp_path)


def test_detect_dokploy_and_docker(tmp_path):
    (tmp_path / "docker-compose.prod.yml").write_text(
        "services:\n  app:\n    networks:\n      - dokploy-network\n"
    )
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    stacks = detect_stacks(tmp_path)
    assert "dokploy" in stacks and "docker" in stacks
