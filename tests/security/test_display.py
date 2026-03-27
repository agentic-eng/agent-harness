from agent_harness.security.display import format_report
from agent_harness.security.models import AuditFinding, SecurityReport


def test_format_empty_report():
    report = SecurityReport(findings=[], ignored_ids=set())
    lines = format_report(report)
    assert any("no vulnerabilities" in line.lower() for line in lines)


def test_format_report_with_fail():
    findings = [
        AuditFinding("evil", "1.0", "CVE-1", "high", "RCE", ["1.1"], is_new_dep=True),
    ]
    report = SecurityReport(findings=findings, ignored_ids=set())
    lines = format_report(report)
    output = "\n".join(lines)
    assert "FAIL" in output
    assert "evil" in output
    assert "CVE-1" in output


def test_format_report_with_warn():
    findings = [
        AuditFinding("old", "1.0", "CVE-2", "high", "XSS", ["1.1"], is_new_dep=False),
    ]
    report = SecurityReport(findings=findings, ignored_ids=set())
    lines = format_report(report)
    output = "\n".join(lines)
    assert "WARN" in output
    assert "old" in output


def test_format_report_with_ignored():
    findings = [
        AuditFinding("pkg", "1.0", "CVE-3", "high", "bad", ["1.1"], is_new_dep=True),
    ]
    report = SecurityReport(findings=findings, ignored_ids={"CVE-3"})
    lines = format_report(report)
    output = "\n".join(lines)
    assert "ignored" in output.lower()


def test_format_summary_line():
    findings = [
        AuditFinding("a", "1.0", "CVE-1", "high", "x", ["1.1"], is_new_dep=True),
        AuditFinding("b", "1.0", "CVE-2", "low", "y", ["1.1"], is_new_dep=False),
    ]
    report = SecurityReport(findings=findings, ignored_ids=set())
    lines = format_report(report)
    summary = lines[-1]
    assert "1" in summary  # 1 fail
