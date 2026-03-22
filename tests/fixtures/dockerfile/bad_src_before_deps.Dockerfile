# BAD: Copies src/ directory before installing dependencies
# Expected: deny — "COPY src/ appears before dependency install"
FROM node:22-bookworm-slim
WORKDIR /app
COPY package.json ./
COPY src/ ./src/
RUN npm ci
USER nonroot
HEALTHCHECK CMD curl -f http://localhost/ || exit 1
