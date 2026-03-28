from unittest.mock import patch

from agent_harness.security.audit import run_security_audit
from agent_harness.security.models import AuditFinding, Classification, SecurityReport


def test_audit_with_findings(tmp_path):
    """Project with osv-scanner findings."""
    mock_findings = [
        AuditFinding(
            package="requests",
            version="2.25.0",
            vuln_id="CVE-2026-1234",
            severity="high",
            description="bad",
            fix_versions=["2.25.1"],
            is_new_dep=False,
        ),
    ]

    with (
        patch(
            "agent_harness.security.audit.run_osv_scanner",
            return_value='{"results":[]}',
        ),
        patch(
            "agent_harness.security.audit.parse_osv_output",
            return_value=mock_findings,
        ),
        patch("agent_harness.security.audit.run_gitleaks", return_value=None),
    ):
        report = run_security_audit(tmp_path, stacks={"python"}, config={})

    assert isinstance(report, SecurityReport)
    assert len(report.findings) == 1


def test_audit_tool_unavailable(tmp_path):
    """osv-scanner not installed — empty report."""
    with (
        patch("agent_harness.security.audit.run_osv_scanner", return_value=None),
        patch("agent_harness.security.audit.run_gitleaks", return_value=None),
    ):
        report = run_security_audit(tmp_path, stacks={"python"}, config={})

    assert report.findings == []


def test_audit_applies_ignores(tmp_path):
    """Ignored CVEs should be reflected in the report."""
    mock_findings = [
        AuditFinding(
            "requests",
            "2.25.0",
            "CVE-2026-1234",
            "high",
            "bad",
            ["2.25.1"],
            is_new_dep=True,
        ),
    ]

    config = {"security": {"ignore": [{"id": "CVE-2026-1234", "reason": "known"}]}}

    with (
        patch(
            "agent_harness.security.audit.run_osv_scanner",
            return_value='{"results":[]}',
        ),
        patch(
            "agent_harness.security.audit.parse_osv_output",
            return_value=mock_findings,
        ),
        patch("agent_harness.security.audit.run_gitleaks", return_value=None),
    ):
        report = run_security_audit(tmp_path, stacks={"python"}, config=config)

    assert report.has_failures is False
    assert report.ignored_count == 1


def test_audit_no_scanner_output(tmp_path):
    """No lockfiles found — empty report."""
    with (
        patch("agent_harness.security.audit.run_osv_scanner", return_value=None),
        patch("agent_harness.security.audit.run_gitleaks", return_value=None),
    ):
        report = run_security_audit(tmp_path, stacks=set(), config={})

    assert report.findings == []


def test_audit_includes_gitleaks(tmp_path):
    """Security audit runs gitleaks alongside osv-scanner."""
    mock_gitleaks_findings = [
        AuditFinding(
            "secret.py",
            "abc123",
            "gitleaks:fp1",
            "critical",
            "aws-access-key in secret.py",
            ["rotate secret"],
            is_new_dep=True,
        ),
    ]

    with (
        patch("agent_harness.security.audit.run_osv_scanner", return_value=None),
        patch("agent_harness.security.audit.run_gitleaks", return_value="[]"),
        patch(
            "agent_harness.security.audit.parse_gitleaks_output",
            return_value=mock_gitleaks_findings,
        ),
    ):
        report = run_security_audit(tmp_path, stacks=set(), config={})

    assert report.has_failures is True
    assert report.fail_count == 1
    assert report.findings[0].classify() == Classification.FAIL
