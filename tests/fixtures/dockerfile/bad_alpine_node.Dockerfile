# BAD: Alpine base with Node.js (musl issues)
# Expected: deny — "Alpine base node:22-alpine with node"
FROM node:22-alpine
WORKDIR /app
COPY package.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
USER nonroot
HEALTHCHECK CMD curl -f http://localhost/ || exit 1
