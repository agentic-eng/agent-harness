"""Docker stack config templates — reference configs for agent-harness init.

These templates are extracted from the ai-harness K skill (docker.md).
They are NOT used by `init` yet — stored here for a future enhancement
that will generate .dockerignore files and provide Docker guidance.
"""

# Standard .dockerignore content.
# Every project with a Dockerfile should have one — without it, build context
# includes .git, node_modules, secrets, and other unnecessary files.
# Use when initializing Docker support in a project.
DOCKERIGNORE = """\
.git
.venv
node_modules
__pycache__
*.pyc
.env
.env.*
coverage.xml
.coverage
htmlcov/
"""

# Guidance notes for Docker (non-deterministic, requires human judgment):
#
# Base image selection:
#   - Prefer -slim variants (smaller, fewer vulnerabilities)
#   - Pin versions: node:22-bookworm-slim, not node:latest
#   - Multi-stage: full image for build, slim for runtime
#   - Alpine uses musl libc — breaks native extensions in Python, Node.js, Ruby
#   - Go and Rust are fine on Alpine (static binaries)
#
# Named volumes:
#   - Named volumes for persistent data (databases, uploads)
#   - Bind mounts for development only
#
# Dependency chains:
#   - Use service_healthy and service_completed_successfully in depends_on
#
# Cache mounts (per stack):
#   - Python (uv): /root/.cache/uv
#   - Python (pip): /root/.cache/pip
#   - Node.js: /root/.npm
#   - Go: /root/.cache/go-build
#   - Rust: /root/.cache/cargo
