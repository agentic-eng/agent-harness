# Docker Guidance

Non-deterministic guidance for Docker and compose — reasoning and recipes that can't be expressed as Rego policies. Deterministic rules are enforced by `agent-harness lint`.

---

## Healthcheck Recipes

### PostgreSQL

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
  interval: 5s
  timeout: 3s
  retries: 5
```

### Redis

```yaml
healthcheck:
  test: ["CMD-SHELL", "redis-cli ping | grep PONG"]
  interval: 5s
  timeout: 3s
  retries: 5
```

### MySQL / MariaDB

```yaml
healthcheck:
  test: ["CMD-SHELL", "mysqladmin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD} --silent"]
  interval: 5s
  timeout: 3s
  retries: 5
```

### HTTP service

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 10s
```

### Auth-protected HTTP

When the health endpoint returns 401 (expected for auth-gated services):

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -sf -o /dev/null -w '%{http_code}' http://localhost:8000/ | grep -qE '200|401'"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 10s
```

### Alpine / BusyBox caveat

`date -d`, `%N`, `--iso-8601` don't exist on Alpine. Health scripts that work on Debian may crash silently on Alpine. Test healthcheck commands inside the actual image.

### Distroless images

No shell, no curl, no wget. Use the application's own binary for health checks: `CMD ["/app", "healthcheck"]`. If the image has no health-capable binary, the healthcheck must be external (sidecar or orchestrator health detection).

---

## Dependency Chains & Migrations

Use `service_healthy` and `service_completed_successfully` conditions:

```yaml
services:
  db:
    healthcheck: ...

  migrate:
    image: ghcr.io/user/app:${IMAGE_TAG}
    command: ["alembic", "upgrade", "head"]
    depends_on:
      db: { condition: service_healthy }

  app:
    depends_on:
      migrate: { condition: service_completed_successfully }
```

**Never run migrations as container entrypoint.** Use a one-shot service — it runs, succeeds, then the app starts. If migration is the entrypoint with `restart: unless-stopped`, it reruns on every container restart.

---

## Configuration Files

Priority — first option that fits wins:

1. **Environment variables** — if the app reads them, don't use a config file. No files to manage, no sync problems, 12-factor compliant. Only limitation: apps requiring structured config (nested YAML, arrays) can't use flat env vars.

2. **envsubst template baked into the image** — for images you own. Bake a template with `${VAR}` placeholders, resolve at startup via entrypoint script. Config structure is version-controlled, values come from env. The Nginx official image uses this pattern.

3. **`command: sh -c 'cat > /path ...'`** — for third-party images you can't modify. Ugly but reliable — config regenerates on every container start.

```yaml
# Pattern 3 example:
services:
  myapp:
    image: thirdparty/app:1.0
    command: >
      sh -c 'cat > /etc/app/config.yml <<CONF
      server:
        port: 8080
      database:
        url: postgresql://${DB_USER}:${DB_PASS}@db:5432/mydb
      CONF
      exec myapp serve'
```

---

## Base Image Selection

- Prefer `-slim` variants (smaller, fewer vulnerabilities)
- Pin versions: `node:22-bookworm-slim`, not `node:latest`
- Multi-stage: full image for build, slim for runtime
- Alpine uses musl libc — breaks native extensions in Python, Node.js, Ruby. Go and Rust are fine.

## .dockerignore

Every project with a Dockerfile should have one. Without it, build context includes `.git`, `node_modules`, secrets. Template in `stacks/docker/templates.py`.

## Common Mistakes

- `COPY . .` before dep install — every build redownloads all dependencies
- Missing `$$` escaping — silently corrupts passwords in compose
- No healthchecks — deployments succeed while app crashes in a loop
- Bind mounts in production — breaks on remote hosts and deployment platforms
- `configs:` with inline `content:` — changes silently ignored on redeploy
