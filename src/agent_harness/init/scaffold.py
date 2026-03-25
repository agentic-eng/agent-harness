import click
from pathlib import Path

from agent_harness.config import load_config
from agent_harness.detect import detect_stacks
from agent_harness.init.diagnostic import display_setup_issues, display_summary
from agent_harness.init.templates import (
    HARNESS_YML,
    YAMLLINT_YML,
    PRECOMMIT_YML,
    MAKEFILE,
)
from agent_harness.registry import PRESETS, UNIVERSAL
from agent_harness.presets.javascript.templates import BIOME_CONFIG


def scaffold_project(project_dir: Path, yes: bool = False) -> list[str]:
    """Write harness config files. Returns list of actions taken."""
    stacks = detect_stacks(project_dir)
    stacks_str = ", ".join(sorted(stacks)) if stacks else "none detected"
    stacks_list = ", ".join(sorted(stacks))

    config = load_config(project_dir)

    # Show what was detected
    click.echo(f"  Detected stacks: {stacks_str}")

    total_critical = 0
    total_recommendations = 0
    total_fixable = 0

    # Run setup checks for each active preset
    for preset in PRESETS:
        if preset.name in stacks:
            issues = preset.run_setup(project_dir, config)
            info = preset.get_info()
            c, r, f = display_setup_issues(preset.name, issues, info.tools, project_dir)
            total_critical += c
            total_recommendations += r
            total_fixable += f

    # Run universal preset setup checks
    universal_issues = UNIVERSAL.run_setup(project_dir, config)
    universal_info = UNIVERSAL.get_info()
    c, r, f = display_setup_issues(
        "universal", universal_issues, universal_info.tools, project_dir
    )
    total_critical += c
    total_recommendations += r
    total_fixable += f

    # Determine test command for Makefile
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

    # JS stack: scaffold biome.json
    if "javascript" in stacks:
        files["biome.json"] = BIOME_CONFIG

    # Determine missing files
    missing_files = [f for f in files if not (project_dir / f).exists()]
    missing_file_count = len(missing_files)

    # Display missing files section
    if missing_files:
        click.echo("\n  Files to create:")
        for filename in missing_files:
            click.echo(f"    + {filename}")

    # Show summary
    display_summary(
        total_critical, total_recommendations, total_fixable, missing_file_count
    )

    # If no files to create, we're done
    if not missing_files:
        return []

    # Confirmation
    if not yes:
        if not click.confirm("\n  Proceed?", default=True):
            return ["Cancelled"]

    actions = []
    for filename, content in files.items():
        path = project_dir / filename
        if path.exists():
            actions.append(f"SKIP  {filename} (already exists)")
        else:
            path.write_text(content)
            actions.append(f"CREATE  {filename}")

    return actions
