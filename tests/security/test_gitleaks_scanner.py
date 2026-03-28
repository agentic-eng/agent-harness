import json

from agent_harness.security.gitleaks_scanner import parse_gitleaks_output
from agent_harness.security.models import Classification


def test_parse_empty_output():
    """No leaks found."""
    findings = parse_gitleaks_output("[]")
    assert findings == []


def test_parse_single_leak():
    """Parse a single leaked secret."""
    output = json.dumps(
        [
            {
                "RuleID": "aws-access-key",
                "Commit": "abc123def456",
                "File": "config/settings.py",
                "Secret": "AKIA...",
                "Match": "AWS_ACCESS_KEY_ID = 'AKIA...'",
                "StartLine": 10,
                "EndLine": 10,
                "Fingerprint": "abc123def456:config/settings.py:aws-access-key:10",
            }
        ]
    )
    findings = parse_gitleaks_output(output)
    assert len(findings) == 1
    assert findings[0].package == "config/settings.py"
    assert findings[0].severity == "critical"
    assert "aws-access-key" in findings[0].description
    assert findings[0].classify() == Classification.FAIL


def test_parse_multiple_leaks():
    """Parse multiple leaked secrets."""
    output = json.dumps(
        [
            {
                "RuleID": "aws-access-key",
                "Commit": "aaa111",
                "File": "config.py",
                "Fingerprint": "fp1",
            },
            {
                "RuleID": "github-token",
                "Commit": "bbb222",
                "File": "deploy.sh",
                "Fingerprint": "fp2",
            },
        ]
    )
    findings = parse_gitleaks_output(output)
    assert len(findings) == 2
    assert all(f.severity == "critical" for f in findings)
    assert all(f.classify() == Classification.FAIL for f in findings)


def test_parse_leak_always_fails():
    """Gitleaks findings must ALWAYS classify as FAIL."""
    output = json.dumps(
        [
            {
                "RuleID": "generic-api-key",
                "Commit": "ccc333",
                "File": "tests/test_helpers.py",
                "Fingerprint": "fp3",
            }
        ]
    )
    findings = parse_gitleaks_output(output)
    # Even in test files — no path exclusions
    assert findings[0].classify() == Classification.FAIL
    assert findings[0].is_new_dep is True


def test_parse_invalid_json():
    """Non-list JSON returns empty."""
    findings = parse_gitleaks_output('{"error": "something"}')
    assert findings == []


def test_parse_missing_fields():
    """Handle leaks with minimal fields."""
    output = json.dumps([{"RuleID": "some-rule"}])
    findings = parse_gitleaks_output(output)
    assert len(findings) == 1
    assert findings[0].severity == "critical"
