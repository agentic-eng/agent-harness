# BAD: No USER instruction — runs as root
# Expected: deny — "no USER instruction"
FROM python:3.12-bookworm-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
COPY src/ ./src/
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
