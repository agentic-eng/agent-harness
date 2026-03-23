# src/agent_harness/cli.py
import click
from pathlib import Path


@click.group()
@click.version_option()
def cli():
    """AI Harness — deterministic controls for AI agents."""


@cli.command()
def detect():
    """Detect project stacks and subprojects."""
    from agent_harness.detect import detect_all

    cwd = Path.cwd()
    results = detect_all(cwd)
    if not results:
        click.echo("no stacks detected")
        return
    for path, stacks in sorted(results.items()):
        rel = "." if path == cwd else str(path.relative_to(cwd))
        stacks_str = ", ".join(sorted(stacks))
        has_harness = (path / ".agent-harness.yml").exists()
        suffix = "" if has_harness else "  (no .agent-harness.yml)"
        click.echo(f"{rel:<30} {stacks_str}{suffix}")


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
@click.option("--all", "run_all", is_flag=True, help="Lint all subprojects (monorepo mode)")
def lint(run_all):
    """Run all harness checks."""
    if run_all:
        from agent_harness.lint import run_lint_all

        cwd = Path.cwd()
        all_results = run_lint_all(cwd)
        total_exit = 0
        for path, results in sorted(all_results.items()):
            rel = "." if path == cwd else str(path.relative_to(cwd))
            click.echo(f"\n=== {rel} ===")
            exit_code = print_results(results)
            if exit_code:
                total_exit = 1
        raise SystemExit(total_exit)
    else:
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
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def init(yes):
    """Scaffold configs and Makefile for detected stacks."""
    from agent_harness.init.scaffold import scaffold_project

    actions = scaffold_project(Path.cwd(), yes=yes)
    for action in actions:
        click.echo(f"  {action}")
    if actions and actions[0] != "Cancelled":
        click.echo("\n  Harness initialized. Run: make lint")


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
