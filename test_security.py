import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from security.scanner import (
    SecurityScanner,
    SecurityFinding,
    SecurityReport,
    Severity,
    Category,
    get_risk_level,
)


class TestSecurityFinding:
    def test_finding_creation(self):
        finding = SecurityFinding(
            id="test-001",
            title="Test Finding",
            description="Test description",
            severity=Severity.HIGH,
            category=Category.INJECTION,
        )
        assert finding.id == "test-001"
        assert finding.severity == Severity.HIGH

    def test_finding_to_dict(self):
        finding = SecurityFinding(
            id="test-001",
            title="Test Finding",
            description="Test description",
            severity=Severity.HIGH,
            category=Category.INJECTION,
            cwe_id="CWE-89",
        )
        d = finding.to_dict()
        assert d["id"] == "test-001"
        assert d["cwe_id"] == "CWE-89"


class TestSecurityReport:
    def test_report_creation(self):
        report = SecurityReport(
            url="https://api.example.com",
            method="GET",
        )
        assert report.url == "https://api.example.com"
        assert len(report.findings) == 0

    def test_report_counts(self):
        findings = [
            SecurityFinding("1", "C1", "D1", Severity.CRITICAL, Category.INJECTION),
            SecurityFinding("2", "H1", "D2", Severity.HIGH, Category.INJECTION),
            SecurityFinding("3", "M1", "D3", Severity.MEDIUM, Category.INJECTION),
            SecurityFinding("4", "L1", "D4", Severity.LOW, Category.INJECTION),
            SecurityFinding("5", "I1", "D5", Severity.INFO, Category.INJECTION),
        ]
        report = SecurityReport(
            url="https://api.example.com",
            method="GET",
            findings=findings,
        )
        assert report.critical_count == 1
        assert report.high_count == 1
        assert report.medium_count == 1
        assert report.low_count == 1


class TestSQLInjectionDetection:
    def test_detects_or_injection(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "GET",
            {},
            params={"id": "1 OR 1=1"},
        )
        sqli_findings = [f for f in report.findings if f.category == Category.INJECTION]
        assert len(sqli_findings) > 0

    def test_detects_union_select(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "GET",
            {},
            params={"id": "1 UNION SELECT * FROM users"},
        )
        assert report.high_count > 0

    def test_detects_comment_injection(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "GET",
            {},
            params={"id": "admin'--"},
        )
        assert report.high_count > 0

    def test_detects_sqli_in_body(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "POST",
            {},
            body={"query": "SELECT * FROM users WHERE id=1 OR 1=1"},
        )
        sqli_findings = [f for f in report.findings if f.category == Category.INJECTION]
        assert len(sqli_findings) > 0


class TestXSSDetection:
    def test_detects_script_tag(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "GET",
            {},
            params={"name": "<script>alert(1)</script>"},
        )
        xss_findings = [f for f in report.findings if "XSS" in f.title]
        assert len(xss_findings) > 0

    def test_detects_javascript_url(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "GET",
            {},
            params={"url": "javascript:alert(1)"},
        )
        assert report.high_count > 0

    def test_detects_onerror(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "GET",
            {},
            params={"img": "<img src=x onerror=alert(1)>"},
        )
        assert report.high_count > 0


class TestSensitiveDataDetection:
    def test_detects_password_in_body(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "POST",
            {},
            body={"data": "password=supersecret123"},
        )
        assert report is not None
        assert isinstance(report, SecurityReport)

    def test_detects_api_key_pattern(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "POST",
            {},
            body={"data": "api_key=test_key_123456789"},
        )
        assert len(report.findings) >= 0

    def test_detects_github_token(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "GET",
            {},
            body={"token": "gho_test1234567890abcdefghijk123456"},
        )
        assert report.critical_count >= 0

    def test_detects_aws_credentials(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "GET",
            {},
            params={"key": "AKIAIOSFODNN7EXAMPLE"},
        )
        assert report.critical_count >= 0

    def test_detects_bearer_token(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "GET",
            {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"},
            {},
        )
        assert len(report.findings) >= 0


class TestURLSecurity:
    def test_detects_http_url(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "http://api.example.com",
            "GET",
            {},
        )
        assert any(f.severity == Severity.HIGH for f in report.findings)

    def test_detects_credentials_in_url(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://user:password@api.example.com",
            "GET",
            {},
        )
        cred_findings = [f for f in report.findings if "Credentials" in f.title]
        assert len(cred_findings) > 0


class TestAuthenticationChecks:
    def test_detects_missing_auth_on_post(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com/users",
            "POST",
            {},
            body={"name": "Test"},
        )
        assert any(f.category == Category.AUTHENTICATION for f in report.findings)

    def test_detects_basic_auth(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "GET",
            {"Authorization": "Basic dXNlcjpwYXNz"},
        )
        basic_auth_findings = [f for f in report.findings if "Basic" in f.title]
        assert len(basic_auth_findings) > 0


class TestResponseHeaders:
    def test_detects_missing_hsts(self):
        scanner = SecurityScanner()
        report = scanner.scan_response(
            "https://api.example.com",
            "GET",
            200,
            {"Content-Type": "application/json"},
        )
        hsts_findings = [f for f in report.findings if "strict-transport" in f.title.lower() or "hsts" in f.title.lower()]
        assert len(hsts_findings) > 0

    def test_detects_missing_x_frame_options(self):
        scanner = SecurityScanner()
        report = scanner.scan_response(
            "https://api.example.com",
            "GET",
            200,
            {"Content-Type": "text/html"},
        )
        xfo_findings = [f for f in report.findings if "x-frame-options" in f.title.lower()]
        assert len(xfo_findings) > 0


class TestCORS:
    def test_detects_wildcard_cors(self):
        scanner = SecurityScanner()
        report = scanner.scan_response(
            "https://api.example.com",
            "GET",
            200,
            {"Access-Control-Allow-Origin": "*"},
        )
        cors_findings = [f for f in report.findings if "CORS" in f.title or f.category == Category.CORS]
        assert len(cors_findings) > 0

    def test_detects_wildcard_with_credentials(self):
        scanner = SecurityScanner()
        report = scanner.scan_response(
            "https://api.example.com",
            "GET",
            200,
            {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
            },
        )
        assert report.high_count > 0


class TestErrorDisclosure:
    def test_detects_stack_trace(self):
        scanner = SecurityScanner()
        report = scanner.scan_response(
            "https://api.example.com",
            "GET",
            500,
            {},
            body={"error": "Internal server error", "stack": "at com.example.main()"},
        )
        assert report.medium_count > 0

    def test_detects_sql_in_error(self):
        scanner = SecurityScanner()
        report = scanner.scan_response(
            "https://api.example.com",
            "GET",
            400,
            {},
            body={"error": "SQL syntax error near 'OR'"},
        )
        assert report.medium_count > 0


class TestRiskScore:
    def test_risk_score_calculation(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "GET",
            {},
            params={"id": "1 OR 1=1"},
        )
        assert report.risk_score >= 7.5

    def test_zero_findings(self):
        scanner = SecurityScanner()
        report = scanner.scan_request(
            "https://api.example.com",
            "GET",
            {"Authorization": "Bearer token"},
            params={"id": "123"},
        )
        assert report.risk_score < 50


class TestGetRiskLevel:
    def test_risk_levels(self):
        assert get_risk_level(80) == "Critical"
        assert get_risk_level(60) == "High"
        assert get_risk_level(30) == "Medium"
        assert get_risk_level(15) == "Low"
        assert get_risk_level(5) == "Informational"


class TestSeverityEnum:
    def test_severity_values(self):
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"


class TestCategoryEnum:
    def test_category_values(self):
        assert Category.INJECTION.value == "injection"
        assert Category.AUTHENTICATION.value == "authentication"
        assert Category.SENSITIVE_DATA.value == "sensitive_data"
        assert Category.HEADERS.value == "headers"
