# BAD: No HEALTHCHECK instruction
# Expected: deny — "no HEALTHCHECK instruction"
FROM python:3.12-bookworm-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
COPY src/ ./src/
USER nonroot
