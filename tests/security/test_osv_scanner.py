import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_harness.security.osv_scanner import (
    _extract_severity,
    is_new_package,
    parse_osv_output,
)


def test_extract_severity_from_database_specific():
    vuln = {"database_specific": {"severity": "HIGH"}}
    assert _extract_severity(vuln) == "high"


def test_extract_severity_unknown():
    vuln = {}
    assert _extract_severity(vuln) == "unknown"


def test_parse_osv_output_basic():
    output = json.dumps(
        {
            "results": [
                {
                    "source": {"path": "uv.lock", "type": "lockfile"},
                    "packages": [
                        {
                            "package": {
                                "name": "requests",
                                "version": "2.25.0",
                                "ecosystem": "PyPI",
                            },
                            "vulnerabilities": [
                                {
                                    "id": "GHSA-xxxx",
                                    "summary": "SSRF vulnerability",
                                    "database_specific": {"severity": "HIGH"},
                                    "affected": [
                                        {
                                            "ranges": [
                                                {
                                                    "events": [
                                                        {"introduced": "0"},
                                                        {"fixed": "2.25.1"},
                                                    ]
                                                }
                                            ]
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )

    with patch("agent_harness.security.osv_scanner.is_new_package", return_value=True):
        findings = parse_osv_output(output, "origin/main", Path("/tmp"))

    assert len(findings) == 1
    assert findings[0].package == "requests"
    assert findings[0].severity == "high"
    assert findings[0].fix_versions == ["2.25.1"]
    assert findings[0].is_new_dep is True


def test_parse_osv_output_no_vulns():
    output = json.dumps({"results": []})
    findings = parse_osv_output(output, "origin/main", Path("/tmp"))
    assert findings == []


def test_parse_osv_output_existing_dep():
    output = json.dumps(
        {
            "results": [
                {
                    "source": {"path": "uv.lock"},
                    "packages": [
                        {
                            "package": {
                                "name": "old-pkg",
                                "version": "1.0",
                                "ecosystem": "PyPI",
                            },
                            "vulnerabilities": [
                                {
                                    "id": "CVE-2025-1111",
                                    "summary": "Old vuln",
                                    "database_specific": {"severity": "CRITICAL"},
                                    "affected": [],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )

    with patch("agent_harness.security.osv_scanner.is_new_package", return_value=False):
        findings = parse_osv_output(output, "origin/main", Path("/tmp"))

    assert len(findings) == 1
    assert findings[0].is_new_dep is False
    assert findings[0].severity == "critical"


@pytest.fixture()
def git_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t.com"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "T"], cwd=str(tmp_path), capture_output=True
    )
    return tmp_path


def test_is_new_package_true(git_repo):
    """Package not in base lockfile is new."""
    (git_repo / "uv.lock").write_text(
        '[[package]]\nname = "requests"\nversion = "2.0"\n'
    )
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(git_repo), capture_output=True
    )
    subprocess.run(["git", "branch", "main"], cwd=str(git_repo), capture_output=True)

    assert is_new_package("evil-pkg", "main", git_repo) is True


def test_is_new_package_false(git_repo):
    """Package in base lockfile is not new."""
    (git_repo / "uv.lock").write_text(
        '[[package]]\nname = "requests"\nversion = "2.0"\n'
    )
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(git_repo), capture_output=True
    )
    subprocess.run(["git", "branch", "main"], cwd=str(git_repo), capture_output=True)

    assert is_new_package("requests", "main", git_repo) is False


def test_is_new_package_no_substring_match(git_repo):
    """'requests' in lockfile should NOT match 'requests-toolbelt'."""
    (git_repo / "uv.lock").write_text(
        '[[package]]\nname = "requests"\nversion = "2.0"\n'
    )
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(git_repo), capture_output=True
    )
    subprocess.run(["git", "branch", "main"], cwd=str(git_repo), capture_output=True)

    # requests-toolbelt is NOT in the lockfile — should be detected as new
    assert is_new_package("requests-toolbelt", "main", git_repo) is True
