# BAD: Alpine base with Python (musl issues)
# Expected: deny — "Alpine base python:3.12-alpine with python"
FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
COPY . .
USER nonroot
HEALTHCHECK CMD curl -f http://localhost/ || exit 1
