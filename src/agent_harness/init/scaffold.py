"""Init command — diagnose project setup, scaffold configs, apply fixes."""

from __future__ import annotations

from pathlib import Path

import click

from agent_harness.config import load_config
from agent_harness.detect import detect_all, detect_stacks
from agent_harness.init.diagnostic import display_setup_issues, display_summary
from agent_harness.init.templates import (
    HARNESS_YML,
    MAKEFILE,
    PRECOMMIT_YML,
    YAMLLINT_YML,
)
from agent_harness.presets.javascript.templates import BIOME_CONFIG
from agent_harness.registry import PRESETS, UNIVERSAL
from agent_harness.setup_check import SetupIssue


def scaffold_project(project_dir: Path, apply: bool = False) -> list[str]:
    """Diagnose setup, optionally apply fixes and scaffold files."""
    stacks = detect_stacks(project_dir)
    stacks_str = ", ".join(sorted(stacks)) if stacks else "none detected"
    stacks_list = ", ".join(sorted(stacks))

    config = load_config(project_dir)

    click.echo(f"  Detected: {stacks_str}")

    total_critical = 0
    total_recommendations = 0
    total_fixable = 0
    all_issues: list[SetupIssue] = []

    # Run setup checks for each active preset
    for preset in PRESETS:
        if preset.name in stacks:
            issues = preset.run_setup(project_dir, config)
            info = preset.get_info()
            c, r, f = display_setup_issues(preset.name, issues, info.tools, project_dir)
            total_critical += c
            total_recommendations += r
            total_fixable += f
            all_issues.extend(issues)

    # Run universal setup checks
    universal_issues = UNIVERSAL.run_setup(project_dir, config)
    universal_info = UNIVERSAL.get_info()
    c, r, f = display_setup_issues(
        "universal", universal_issues, universal_info.tools, project_dir
    )
    total_critical += c
    total_recommendations += r
    total_fixable += f
    all_issues.extend(universal_issues)

    # Determine files to scaffold
    if "python" in stacks:
        test_command = "uv run pytest tests/ -v"
    elif "javascript" in stacks:
        test_command = "npm test"
    else:
        test_command = 'echo "no test command configured"'

    files: dict[str, str] = {
        ".agent-harness.yml": HARNESS_YML.format(
            stacks=stacks_str, stacks_list=stacks_list
        ),
        ".yamllint.yml": YAMLLINT_YML,
        ".pre-commit-config.yaml": PRECOMMIT_YML,
        "Makefile": MAKEFILE.format(test_command=test_command),
    }

    if "javascript" in stacks:
        files["biome.json"] = BIOME_CONFIG

    missing_files = [f for f in files if not (project_dir / f).exists()]

    if missing_files:
        click.echo("\n  Files to create:")
        for filename in missing_files:
            click.echo(f"    + {filename}")

    display_summary(
        total_critical, total_recommendations, total_fixable, len(missing_files)
    )

    if not apply:
        # Report mode — show what would be done
        if total_fixable or missing_files:
            click.echo(
                "\n  To apply fixes and create files:\n    agent-harness init --apply"
            )
        return []

    # Apply mode — fix issues and scaffold files
    actions: list[str] = []

    fixable_issues = [i for i in all_issues if i.fixable]
    for issue in fixable_issues:
        assert issue.fix is not None
        issue.fix(project_dir)
        actions.append(f"FIXED  {issue.file}: {issue.message}")

    for filename, content in files.items():
        path = project_dir / filename
        if path.exists():
            actions.append(f"SKIP  {filename} (already exists)")
        else:
            path.write_text(content)
            actions.append(f"CREATE  {filename}")

    return actions


def scaffold_all(project_dir: Path, apply: bool = False) -> dict[Path, list[str]]:
    """Discover all project roots and scaffold each one."""
    all_roots = detect_all(project_dir)

    mode = "Applying fixes" if apply else "Diagnosing setup"
    click.echo(f"\n  {mode} for agent-harness quality gates.")

    # Show discovered projects upfront
    if len(all_roots) > 1:
        root_names = []
        for root in sorted(all_roots):
            rel = "." if root == project_dir else str(root.relative_to(project_dir))
            root_names.append(rel)
        click.echo(f"  Found {len(all_roots)} projects: {', '.join(root_names)}")

    results: dict[Path, list[str]] = {}
    for root in sorted(all_roots):
        rel = "." if root == project_dir else str(root.relative_to(project_dir))
        click.echo(f"\n=== {rel} ===")
        actions = scaffold_project(root, apply=apply)
        results[root] = actions
    return results
