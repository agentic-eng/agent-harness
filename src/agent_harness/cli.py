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
@click.option(
    "--all",
    "run_all",
    is_flag=True,
    hidden=True,
    help="Deprecated — discovery is now always on",
)
def lint(run_all):
    """Run all harness checks (auto-discovers subprojects)."""
    from agent_harness.lint import run_lint_all

    cwd = Path.cwd()
    all_results = run_lint_all(cwd)
    total_exit = 0
    for path, results in sorted(all_results.items()):
        rel = "." if path == cwd else str(path.relative_to(cwd))
        if len(all_results) > 1:
            click.echo(f"\n=== {rel} ===")
        exit_code = print_results(results)
        if exit_code:
            total_exit = 1
    raise SystemExit(total_exit)


@cli.command()
@click.option(
    "--all",
    "run_all",
    is_flag=True,
    hidden=True,
    help="Deprecated — discovery is now always on",
)
def fix(run_all):
    """Auto-fix what's fixable, then lint (auto-discovers subprojects)."""
    from agent_harness.fix import run_fix_all
    from agent_harness.lint import run_lint_all

    cwd = Path.cwd()

    click.echo("Fixing...")
    fix_results = run_fix_all(cwd)
    for path, actions in sorted(fix_results.items()):
        rel = "." if path == cwd else str(path.relative_to(cwd))
        for a in actions:
            click.echo(f"  {rel}: {a}")

    click.echo("\nLinting...")
    lint_results = run_lint_all(cwd)
    total_exit = 0
    for path, results in sorted(lint_results.items()):
        rel = "." if path == cwd else str(path.relative_to(cwd))
        if len(lint_results) > 1:
            click.echo(f"\n=== {rel} ===")
        exit_code = print_results(results)
        if exit_code:
            total_exit = 1
    raise SystemExit(total_exit)


@cli.command()
@click.option("--apply", is_flag=True, help="Apply fixes and create missing files")
def init(apply):
    """Diagnose harness setup: check tools, config quality, missing files.

    Without --apply: report mode (shows issues, suggests fixes).
    With --apply: applies auto-fixes and creates missing config files.

    Setup checks diagnose configuration quality (thresholds, flags,
    coverage settings) and offer fixes. Lint checks run separately
    via 'agent-harness lint' for fast pass/fail enforcement.

    Examples:
      agent-harness init            # diagnose only
      agent-harness init --apply    # diagnose and fix
    """
    from agent_harness.init.scaffold import scaffold_all

    all_results = scaffold_all(Path.cwd(), apply=apply)
    any_actions = False
    for path, actions in sorted(all_results.items()):
        for action in actions:
            click.echo(f"  {action}")
        if actions:
            any_actions = True
    if any_actions:
        click.echo("\n  Done. Run: make lint")
