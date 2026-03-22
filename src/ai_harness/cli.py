# src/ai_harness/cli.py
import click
from pathlib import Path

@click.group()
@click.version_option()
def cli():
    """AI Harness — deterministic controls for AI agents."""

@cli.command()
def detect():
    """Detect project stacks (Python, Docker, etc.)."""
    from ai_harness.detect import detect_stacks
    stacks = detect_stacks(Path.cwd())
    if stacks:
        for stack in sorted(stacks):
            click.echo(stack)
    else:
        click.echo("no stacks detected")

@cli.command()
def lint():
    """Run all harness checks."""
    from ai_harness.lint import run_lint
    results = run_lint(Path.cwd())

    failed = [r for r in results if not r.passed]
    passed = [r for r in results if r.passed]
    total_ms = sum(r.duration_ms for r in results)

    for r in results:
        icon = "PASS" if r.passed else "FAIL"
        click.echo(f"  {icon}  {r.name} ({r.duration_ms}ms)")
        if not r.passed and r.error:
            for line in r.error.strip().splitlines():
                click.echo(f"       {line}")

    click.echo(f"\n{len(passed)} passed, {len(failed)} failed ({total_ms}ms)")
    raise SystemExit(1 if failed else 0)

@cli.command()
def fix():
    """Auto-fix what's fixable, then lint."""
    click.echo("fix: not implemented")

@cli.command()
def init():
    """Initialize harness on a project."""
    click.echo("init: not implemented")

@cli.command()
def audit():
    """Audit harness configuration completeness."""
    click.echo("audit: not implemented")
