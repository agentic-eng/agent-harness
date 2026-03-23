from agent_harness.stacks.docker.conftest_dockerfile_check import (
    run_conftest_dockerfile,
)


def test_conftest_dockerfile_good(tmp_path):
    (tmp_path / "Dockerfile").write_text(
        "FROM python:3.12-bookworm-slim\nWORKDIR /app\n"
        "COPY pyproject.toml uv.lock ./\n"
        "RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev\n"
        "COPY src/ ./src/\nUSER nonroot\n"
        "HEALTHCHECK CMD curl -f http://localhost/ || exit 1\n"
    )
    result = run_conftest_dockerfile(tmp_path)
    assert result.passed, f"Expected pass but got: {result.error}"


def test_conftest_dockerfile_bad_no_user(tmp_path):
    (tmp_path / "Dockerfile").write_text(
        "FROM python:3.12-bookworm-slim\nWORKDIR /app\nCOPY . .\n"
        "RUN uv sync\nHEALTHCHECK CMD curl -f http://localhost/ || exit 1\n"
    )
    result = run_conftest_dockerfile(tmp_path)
    assert not result.passed


def test_conftest_no_dockerfile(tmp_path):
    result = run_conftest_dockerfile(tmp_path)
    assert result.passed  # graceful skip
