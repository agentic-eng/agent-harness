# GOOD: Multi-stage COPY --from should not trigger layer ordering
# Expected: no deny
FROM python:3.12-bookworm-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

FROM python:3.12-bookworm-slim
WORKDIR /app
COPY --from=builder /app /app
USER nonroot
HEALTHCHECK CMD curl -f http://localhost/ || exit 1
