# BAD: Dependency install without cache mount
# Expected: deny — "uv sync without --mount=type=cache"
FROM python:3.12-bookworm-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY src/ ./src/
USER nonroot
HEALTHCHECK CMD curl -f http://localhost/ || exit 1
