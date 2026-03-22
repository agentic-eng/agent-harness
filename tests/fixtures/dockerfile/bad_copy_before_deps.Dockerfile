# BAD: Copies all source before installing dependencies
# Expected: deny — "COPY . . appears before dependency install"
FROM python:3.12-bookworm-slim
WORKDIR /app
COPY . .
RUN uv sync --frozen --no-dev
USER nonroot
HEALTHCHECK CMD curl -f http://localhost/ || exit 1
