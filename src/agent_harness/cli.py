# src/agent_harness/cli.py
import click
from pathlib import Path


@click.group()
@click.version_option()
def cli():
    """AI Harness — deterministic controls for AI agents."""


@cli.command()
def detect():
    """Detect project stacks (Python, Docker, etc.)."""
    from agent_harness.detect import detect_stacks

    stacks = detect_stacks(Path.cwd())
    if stacks:
        for stack in sorted(stacks):
            click.echo(stack)
    else:
        click.echo("no stacks detected")


def print_results(results) -> int:
    """Print lint results and return exit code."""
    failed = [r for r in results if not r.passed]
    passed = [r for r in results if r.passed]
    total_ms = sum(r.duration_ms for r in results)

    for r in results:
        icon = "PASS" if r.passed else "FAIL"
        click.echo(f"  {icon}  {r.name} ({r.duration_ms}ms)")
        if not r.passed:
            detail = r.error or r.output
            if detail:
                for line in detail.strip().splitlines():
                    click.echo(f"       {line}")

    click.echo(f"\n{len(passed)} passed, {len(failed)} failed ({total_ms}ms)")
    return 1 if failed else 0


@cli.command()
def lint():
    """Run all harness checks."""
    from agent_harness.lint import run_lint

    results = run_lint(Path.cwd())
    raise SystemExit(print_results(results))


@cli.command()
def fix():
    """Auto-fix what's fixable, then lint."""
    from agent_harness.fix import run_fix
    from agent_harness.lint import run_lint

    click.echo("Fixing...")
    actions = run_fix(Path.cwd())
    for a in actions:
        click.echo(f"  {a}")

    click.echo("\nLinting...")
    results = run_lint(Path.cwd())
    raise SystemExit(print_results(results))


@cli.command()
def init():
    """Initialize harness on a project."""
    from agent_harness.init.scaffold import scaffold_project

    actions = scaffold_project(Path.cwd())
    for action in actions:
        click.echo(f"  {action}")
    click.echo("\nHarness initialized. Run 'agent-harness lint' to check.")


@cli.command()
def audit():
    """Audit harness configuration — shows what's missing and how to fix it."""
    from agent_harness.audit import run_audit

    items = run_audit(Path.cwd())

    ok = [i for i in items if i.status == "ok"]
    issues = [i for i in items if i.status != "ok"]

    for item in items:
        if item.status == "ok":
            click.echo(f"  OK    {item.message}")
        elif item.status == "missing":
            click.echo(f"  MISS  {item.message}")
            if item.fix:
                click.echo(f"        Fix: {item.fix}")
        elif item.status == "misconfigured":
            click.echo(f"  WARN  {item.message}")
            if item.fix:
                for line in item.fix.strip().splitlines():
                    click.echo(f"        {line}")

    click.echo(f"\n{len(ok)} ok, {len(issues)} issues")
    if issues:
        click.echo("\nRun 'agent-harness init' to fix missing config files.")
    raise SystemExit(1 if issues else 0)
