from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import shutil
from agent_harness.detect import detect_stacks
from agent_harness.config import load_config


@dataclass
class AuditItem:
    area: str
    status: str  # "ok", "missing", "misconfigured"
    message: str
    fix: str = ""  # How to fix it


def run_audit(project_dir: Path) -> list[AuditItem]:
    items: list[AuditItem] = []
    config = load_config(project_dir)
    stacks = config.stacks or detect_stacks(project_dir)

    # ── Tools installed? ──
    tools = {
        "conftest": "brew install conftest",
        "hadolint": "brew install hadolint",
        "yamllint": "pip install yamllint or uv add yamllint --dev",
    }
    if "python" in stacks:
        tools["ruff"] = "uv add ruff --dev"
        tools["ty"] = "uv add ty --dev"
    if "javascript" in stacks:
        tools["biome"] = "npm install --save-dev @biomejs/biome"

    for tool, install_cmd in tools.items():
        if shutil.which(tool):
            items.append(AuditItem(area="tools", status="ok", message=f"{tool} installed"))
        else:
            items.append(AuditItem(area="tools", status="missing", message=f"{tool} not found", fix=install_cmd))

    # ── Config files ──
    configs = {
        ".agent-harness.yml": "Run: agent-harness init",
        ".yamllint.yml": "Run: agent-harness init",
        ".pre-commit-config.yaml": "Run: agent-harness init",
    }
    for filename, fix in configs.items():
        path = project_dir / filename
        if path.exists():
            items.append(AuditItem(area="config", status="ok", message=f"{filename} exists"))
        else:
            items.append(AuditItem(area="config", status="missing", message=f"{filename} not found", fix=fix))

    # ── Pre-commit hooks active? ──
    hooks_path = project_dir / ".git" / "hooks" / "pre-commit"
    if hooks_path.exists():
        items.append(AuditItem(area="hooks", status="ok", message="pre-commit hooks installed"))
    else:
        items.append(AuditItem(area="hooks", status="missing", message="pre-commit hooks not installed", fix="prek install or pre-commit install"))

    # ── Agent context file? ──
    agent_files = ["CLAUDE.md", "AGENTS.md", ".cursorrules"]
    found_agent = any((project_dir / f).exists() for f in agent_files)
    if found_agent:
        items.append(AuditItem(area="agent", status="ok", message="Agent context file found"))
    else:
        items.append(AuditItem(area="agent", status="missing", message="No agent context file (CLAUDE.md / AGENTS.md)", fix="Create CLAUDE.md with Dev Commands section"))

    # ── Python-specific ──
    if "python" in stacks:
        pyproject = project_dir / "pyproject.toml"
        if pyproject.exists():
            from agent_harness.stacks.python.conftest_python_check import run_conftest_python

            result = run_conftest_python(project_dir)
            if result.passed:
                items.append(AuditItem(area="python", status="ok", message="pyproject.toml harness config correct"))
            else:
                items.append(AuditItem(area="python", status="misconfigured", message="pyproject.toml harness issues", fix=result.output or result.error))

    # ── Docker-specific ──
    if "docker" in stacks:
        dockerfile = project_dir / "Dockerfile"
        if not dockerfile.exists():
            items.append(AuditItem(area="docker", status="missing", message="No Dockerfile", fix="Create Dockerfile"))

    # ── JavaScript-specific ──
    if "javascript" in stacks:
        pkg = project_dir / "package.json"
        if pkg.exists():
            from agent_harness.stacks.javascript.conftest_package_check import run_conftest_package

            result = run_conftest_package(project_dir)
            if result.passed:
                items.append(AuditItem(area="javascript", status="ok", message="package.json harness config correct"))
            else:
                items.append(AuditItem(area="javascript", status="misconfigured", message="package.json issues", fix=result.output or result.error))

    # ── .gitignore ──
    gitignore = project_dir / ".gitignore"
    if gitignore.exists():
        from agent_harness.stacks.universal.conftest_gitignore_check import run_conftest_gitignore

        result = run_conftest_gitignore(project_dir, stacks=stacks)
        if result.passed:
            items.append(AuditItem(area="gitignore", status="ok", message=".gitignore has required entries"))
        else:
            items.append(AuditItem(area="gitignore", status="misconfigured", message=".gitignore missing entries", fix=result.output or result.error))
    else:
        items.append(AuditItem(area="gitignore", status="missing", message="No .gitignore", fix="Create .gitignore with .env, .venv, __pycache__"))

    return items
