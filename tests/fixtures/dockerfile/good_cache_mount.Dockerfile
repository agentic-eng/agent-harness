# GOOD: Dependency install with cache mount
# Expected: no deny
FROM node:22-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
USER nonroot
HEALTHCHECK CMD curl -f http://localhost/ || exit 1
