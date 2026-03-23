from __future__ import annotations
import subprocess
import shutil
import time
from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    passed: bool
    output: str = ""
    error: str = ""
    duration_ms: int = 0


def run_check(name: str, cmd: list[str], cwd: str | None = None) -> CheckResult:
    """Run a check command and return structured result."""
    tool = cmd[0]
    if not shutil.which(tool):
        return CheckResult(
            name=name,
            passed=False,
            error=f"{tool} not found — not installed or not in PATH",
        )
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=60
        )
        duration = int((time.monotonic() - start) * 1000)
        return CheckResult(
            name=name,
            passed=result.returncode == 0,
            output=result.stdout,
            error=result.stderr,
            duration_ms=duration,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(name=name, passed=False, error=f"{name} timed out after 60s")
