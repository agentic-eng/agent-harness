# BAD: Secret passed as build ARG
# Expected: deny — "ARG 'DB_PASSWORD' looks like a secret"
FROM python:3.12-bookworm-slim
ARG DB_PASSWORD
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
COPY src/ ./src/
USER nonroot
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
