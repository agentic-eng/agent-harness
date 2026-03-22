# GOOD: Alpine is fine for Go (static binaries, no musl issues)
# Expected: no deny
FROM golang:1.22-alpine
WORKDIR /app
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/root/.cache/go-build go mod download
COPY . .
RUN go build -o /server ./cmd/server
USER nonroot
HEALTHCHECK CMD curl -f http://localhost/ || exit 1
