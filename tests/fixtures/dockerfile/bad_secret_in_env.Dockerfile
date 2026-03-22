# BAD: Secret baked into ENV
# Expected: deny — "ENV 'API_KEY' looks like a secret"
FROM python:3.12-bookworm-slim
WORKDIR /app
ENV API_KEY=sk-1234567890
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
COPY src/ ./src/
USER nonroot
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
