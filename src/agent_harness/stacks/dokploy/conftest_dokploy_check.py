"""
Conftest Dokploy check.

WHAT: Runs conftest on docker-compose files with bundled Dokploy policies
covering Traefik label requirements and network attachment.

WHY: Agents add Traefik routing labels but forget `traefik.enable=true`
(silent 404 — traefik-ts has exposedbydefault=false) or forget to attach
services to `dokploy-network` (silent 502 — Traefik can't reach the service).

WITHOUT IT: Silent 404s and 502s that take hours to debug because the
labels "look correct."

FIX: Read the specific conftest violation messages — each maps to a concrete
compose file change (add `traefik.enable=true`, add `dokploy-network`).

REQUIRES: conftest (via PATH)
"""

from __future__ import annotations

from pathlib import Path

from agent_harness.runner import CheckResult, run_check

POLICIES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "policies"
COMPOSE_FILES = ["docker-compose.prod.yml", "docker-compose.yml"]


def run_conftest_dokploy(project_dir: Path) -> CheckResult:
    """Run conftest on compose files with bundled Dokploy policies."""
    name = "conftest-dokploy"
    # Find the first compose file that exists
    for f in COMPOSE_FILES:
        target = project_dir / f
        if target.exists():
            policy_path = POLICIES_DIR / "dokploy"
            cmd = [
                "conftest",
                "test",
                str(target),
                "--policy",
                str(policy_path),
                "--no-color",
                "--all-namespaces",
            ]
            return run_check(name, cmd, cwd=str(project_dir))

    return CheckResult(
        name=name,
        passed=True,
        output=f"Skipping {name}: no compose file found",
    )
