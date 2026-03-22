# GOOD: Dependency manifest first, install, then source
# Expected: no deny
FROM python:3.12-bookworm-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
USER nonroot
HEALTHCHECK CMD curl -f http://localhost/ || exit 1
