from agent_harness.security.models import AuditFinding, Classification, SecurityReport


def test_finding_classification_new_high_fixable_is_fail():
    f = AuditFinding(
        package="evil-pkg",
        version="1.0.0",
        vuln_id="CVE-2026-1234",
        severity="high",
        description="RCE vulnerability",
        fix_versions=["1.0.1"],
        is_new_dep=True,
    )
    assert f.classify() == Classification.FAIL


def test_finding_classification_new_critical_fixable_is_fail():
    f = AuditFinding(
        package="evil-pkg",
        version="1.0.0",
        vuln_id="CVE-2026-5678",
        severity="critical",
        description="SQL injection",
        fix_versions=["2.0.0"],
        is_new_dep=True,
    )
    assert f.classify() == Classification.FAIL


def test_finding_classification_new_high_no_fix_is_warn():
    f = AuditFinding(
        package="evil-pkg",
        version="1.0.0",
        vuln_id="CVE-2026-9999",
        severity="high",
        description="No fix yet",
        fix_versions=[],
        is_new_dep=True,
    )
    assert f.classify() == Classification.WARN


def test_finding_classification_existing_high_fixable_is_warn():
    f = AuditFinding(
        package="old-pkg",
        version="1.0.0",
        vuln_id="CVE-2025-1111",
        severity="high",
        description="Known issue in existing dep",
        fix_versions=["1.1.0"],
        is_new_dep=False,
    )
    assert f.classify() == Classification.WARN


def test_finding_classification_new_low_fixable_is_warn():
    f = AuditFinding(
        package="some-pkg",
        version="1.0.0",
        vuln_id="CVE-2026-2222",
        severity="low",
        description="Minor info leak",
        fix_versions=["1.0.1"],
        is_new_dep=True,
    )
    assert f.classify() == Classification.WARN


def test_finding_classification_new_medium_fixable_is_warn():
    f = AuditFinding(
        package="med-pkg",
        version="2.0.0",
        vuln_id="CVE-2026-3333",
        severity="medium",
        description="XSS",
        fix_versions=["2.0.1"],
        is_new_dep=True,
    )
    assert f.classify() == Classification.WARN


def test_report_has_failures():
    findings = [
        AuditFinding("pkg", "1.0", "CVE-1", "high", "bad", ["1.1"], is_new_dep=True),
        AuditFinding("pkg2", "1.0", "CVE-2", "low", "meh", ["1.1"], is_new_dep=False),
    ]
    report = SecurityReport(findings=findings, ignored_ids=set())
    assert report.has_failures is True
    assert report.fail_count == 1
    assert report.warn_count == 1


def test_report_no_failures():
    findings = [
        AuditFinding("pkg", "1.0", "CVE-1", "low", "meh", ["1.1"], is_new_dep=True),
    ]
    report = SecurityReport(findings=findings, ignored_ids=set())
    assert report.has_failures is False
    assert report.fail_count == 0
    assert report.warn_count == 1


def test_report_ignores_cves():
    findings = [
        AuditFinding("pkg", "1.0", "CVE-1", "high", "bad", ["1.1"], is_new_dep=True),
    ]
    report = SecurityReport(findings=findings, ignored_ids={"CVE-1"})
    assert report.has_failures is False
    assert report.fail_count == 0
    assert report.warn_count == 0
    assert report.ignored_count == 1
