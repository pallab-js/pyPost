import re
import json
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse, parse_qs


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(Enum):
    INJECTION = "injection"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SENSITIVE_DATA = "sensitive_data"
    SSL_TLS = "ssl_tls"
    HEADERS = "headers"
    CORS = "cors"
    RATE_LIMITING = "rate_limiting"
    ENCRYPTION = "encryption"
    INFORMATION = "information"


@dataclass
class SecurityFinding:
    id: str
    title: str
    description: str
    severity: Severity
    category: Category
    evidence: Dict[str, Any] = field(default_factory=dict)
    remediation: str = ""
    cwe_id: Optional[str] = None
    owasp_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "evidence": self.evidence,
            "remediation": self.remediation,
            "cwe_id": self.cwe_id,
            "owasp_ref": self.owasp_ref,
        }


@dataclass
class SecurityReport:
    url: str
    method: str
    findings: List[SecurityFinding] = field(default_factory=list)
    scan_duration_ms: float = 0.0
    timestamp: str = ""
    risk_score: float = 0.0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.LOW)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "method": self.method,
            "findings": [f.to_dict() for f in self.findings],
            "scan_duration_ms": self.scan_duration_ms,
            "timestamp": self.timestamp,
            "risk_score": self.risk_score,
            "summary": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "total": len(self.findings),
            },
        }


class SecurityScanner:
    SQLI_PATTERNS = [
        r"(\bOR\b|\bAND\b).*[=<>].*['\"]?",
        r"['\"]\s*(OR|AND)\s*['\"]?\s*[=<>]",
        r"(UNION|SELECT|INSERT|UPDATE|DELETE|DROP)\s+(ALL|DISTINCT)?",
        r"--\s*$",
        r"/\*.*\*/",
        r";\s*(DROP|DELETE|TRUNCATE)",
        r"('\s*(OR|AND)\s*'.*'=)",
        r"'\s*OR\s+'1'\s*=\s*'1",
        r"'\s*OR\s+1\s*=\s*1",
        r"'\s*OR\s+'a'\s*=\s*'a",
        r"'\s*OR\s+\d+\s*=\s*\d+",
        r"admin\s*('|\s+OR\s+|'|).*('|).*('|)",
        r"'\s*;\s*DROP\s+TABLE",
        r"'\s*UNION\s+SELECT",
        r"waitfor\s+delay\s+'[\d:]+'",
        r"SLEEP\s*\(\s*\d+\s*\)",
        r"pg_sleep\s*\(\s*\d+\s*\)",
        r"benchmark\s*\(",
        r"load_file\s*\(",
        r"into\s+(OUTFILE|DUMPFILE)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript\s*:",
        r"on\w+\s*=",
        r"<img[^>]+src\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<embed[^>]*>",
        r"<object[^>]*>.*?</object>",
        r"<\?xml[^>]*>",
        r"<svg[^>]*>.*?</svg>",
        r"expression\s*\(",
        r"url\s*\(",
        r"data\s*:\s*text/html",
    ]

    SENSITIVE_PATTERNS = [
        (r"password\s*=\s*['\"][^'\"]{1,}", "Password in query/body", Severity.HIGH),
        (r"api[_-]?key\s*=\s*['\"][^'\"]{8,}", "API Key exposed", Severity.HIGH),
        (r"token\s*=\s*['\"][^'\"]{10,}", "Token exposed", Severity.HIGH),
        (r"secret\s*=\s*['\"][^'\"]{8,}", "Secret exposed", Severity.HIGH),
        (r"bearer\s+[a-zA-Z0-9\-._~+/]+", "Bearer token in Authorization", Severity.HIGH),
        (r"access[_-]?token\s*=\s*['\"][^'\"]{10,}", "Access token exposed", Severity.HIGH),
        (r"refresh[_-]?token\s*=\s*['\"][^'\"]{10,}", "Refresh token exposed", Severity.HIGH),
        (r"private[_-]?key\s*=", "Private key reference", Severity.CRITICAL),
        (r"-----BEGIN\s+(RSA|DSA|EC|OPENSSH)?\s*PRIVATE\s+KEY-----", "Private key content", Severity.CRITICAL),
        (r"aws[_-]?access[_-]?key[_-]?id\s*=", "AWS Access Key ID", Severity.CRITICAL),
        (r"aws[_-]?secret[_-]?access[_-]?key\s*=", "AWS Secret Access Key", Severity.CRITICAL),
        (r"sk_live_[a-zA-Z0-9]{20,}", "Stripe Live Secret Key", Severity.CRITICAL),
        (r"pk_live_[a-zA-Z0-9]{20,}", "Stripe Live Public Key", Severity.MEDIUM),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token", Severity.CRITICAL),
        (r"xox[baprs]-[a-zA-Z0-9]{10,}", "Slack Token", Severity.CRITICAL),
        (r"sq0csp-[a-zA-Z0-9-_]{43}", "Square OAuth Secret", Severity.CRITICAL),
        (r"sq0atp-[a-zA-Z0-9-_]{22}", "Square Access Token", Severity.CRITICAL),
        (r"amzn\.mws\.[a-f0-9-]{32}", "Amazon MWS Auth Token", Severity.CRITICAL),
        (r"credit[_-]?card\s*[=:]\s*['\"]?\d{13,19}", "Credit Card Number", Severity.CRITICAL),
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "Potential Credit Card", Severity.MEDIUM),
        (r"\b\d{3,4}\s*[-]?\d{6}\s*[-]?\d{5}\b", "Potential SSN", Severity.CRITICAL),
        (r"-----BEGIN\s+CERTIFICATE-----", "Certificate content", Severity.MEDIUM),
    ]

    INSECURE_HEADERS = {
        "x-frame-options": {"expected": ["DENY", "SAMEORIGIN"], "severity": Severity.MEDIUM},
        "x-content-type-options": {"expected": ["nosniff"], "severity": Severity.LOW},
        "strict-transport-security": {"expected": None, "severity": Severity.HIGH},
        "x-xss-protection": {"expected": ["1", "1; mode=block"], "severity": Severity.LOW},
        "content-security-policy": {"expected": None, "severity": Severity.MEDIUM},
        "referrer-policy": {"expected": None, "severity": Severity.LOW},
        "permissions-policy": {"expected": None, "severity": Severity.LOW},
    }

    def __init__(self):
        self._sqli_compiled = [re.compile(p, re.IGNORECASE) for p in self.SQLI_PATTERNS]
        self._xss_compiled = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.XSS_PATTERNS]
        self._sensitive_compiled = [
            (re.compile(p, re.IGNORECASE), desc, sev)
            for p, desc, sev in self.SENSITIVE_PATTERNS
        ]

    def _generate_id(self, data: str) -> str:
        return hashlib.md5(data.encode()).hexdigest()[:8]

    def scan_request(self, url: str, method: str, headers: Dict[str, str], 
                     body: Optional[Any] = None, params: Optional[Dict[str, str]] = None) -> SecurityReport:
        findings = []
        params = params or {}
        body_str = json.dumps(body) if body else ""

        findings.extend(self._check_sql_injection(url, params, body_str))
        findings.extend(self._check_xss(url, params, body_str))
        findings.extend(self._check_sensitive_data(url, method, headers, body_str, params))
        findings.extend(self._check_url_security(url))
        findings.extend(self._check_authentication(url, method, headers))

        risk_score = self._calculate_risk_score(findings)

        return SecurityReport(
            url=url,
            method=method,
            findings=findings,
            risk_score=risk_score,
        )

    def scan_response(self, url: str, method: str, status_code: int,
                      headers: Dict[str, str], body: Optional[Any] = None) -> SecurityReport:
        findings = []
        body_str = json.dumps(body) if body else ""

        findings.extend(self._check_response_headers(headers))
        findings.extend(self._check_cors(headers))
        findings.extend(self._check_sensitive_data_in_response(body_str))
        findings.extend(self._check_error_disclosure(status_code, body_str))
        findings.extend(self._check_cache_headers(headers))

        risk_score = self._calculate_risk_score(findings)

        return SecurityReport(
            url=url,
            method=method,
            findings=findings,
            risk_score=risk_score,
        )

    def _check_sql_injection(self, url: str, params: Dict[str, str], body: str) -> List[SecurityFinding]:
        findings = []
        combined = url + "?" + "&".join(f"{k}={v}" for k, v in params.items()) + body

        for i, pattern in enumerate(self._sqli_compiled):
            matches = pattern.findall(combined)
            if matches:
                findings.append(SecurityFinding(
                    id=f"sqli-{i}",
                    title="Potential SQL Injection",
                    description=f"Possible SQL injection pattern detected: {matches[0][:50]}",
                    severity=Severity.HIGH,
                    category=Category.INJECTION,
                    evidence={"matches": matches[:3], "location": "url/params/body"},
                    remediation="Use parameterized queries or ORM. Never concatenate user input into SQL.",
                    cwe_id="CWE-89",
                    owasp_ref="A03:2021-Injection",
                ))

        return findings

    def _check_xss(self, url: str, params: Dict[str, str], body: str) -> List[SecurityFinding]:
        findings = []
        combined = url + "?" + "&".join(f"{k}={v}" for k, v in params.items()) + body

        for i, pattern in enumerate(self._xss_compiled):
            matches = pattern.findall(combined)
            if matches:
                findings.append(SecurityFinding(
                    id=f"xss-{i}",
                    title="Potential Cross-Site Scripting (XSS)",
                    description=f"Possible XSS pattern detected: {matches[0][:50]}",
                    severity=Severity.HIGH,
                    category=Category.INJECTION,
                    evidence={"matches": matches[:3], "location": "url/params/body"},
                    remediation="Encode output, use Content-Security-Policy, validate/sanitize input.",
                    cwe_id="CWE-79",
                    owasp_ref="A03:2021-Injection",
                ))

        return findings

    def _check_sensitive_data(self, url: str, method: str, headers: Dict[str, str],
                               body: str, params: Dict[str, str]) -> List[SecurityFinding]:
        findings = []
        combined = f"{url} {'|'.join(str(v) for v in params.values())} {body}"

        auth_header = headers.get("authorization", "") + headers.get("Authorization", "")
        if auth_header and "bearer" in auth_header.lower():
            findings.append(SecurityFinding(
                id="auth-001",
                title="Authorization Header Present",
                description="Bearer token found in Authorization header",
                severity=Severity.INFO,
                category=Category.AUTHENTICATION,
                evidence={"header_length": len(auth_header)},
                remediation="Ensure tokens are transmitted over HTTPS only.",
                cwe_id="CWE-598",
            ))

        for i, (pattern, desc, severity) in enumerate(self._sensitive_compiled):
            matches = pattern.findall(combined)
            if matches:
                findings.append(SecurityFinding(
                    id=f"sens-{i}",
                    title=desc,
                    description=f"Sensitive data pattern detected in request",
                    severity=severity,
                    category=Category.SENSITIVE_DATA,
                    evidence={"pattern_type": desc, "redacted": "[REDACTED]"},
                    remediation="Remove sensitive data from requests. Use environment variables.",
                    cwe_id="CWE-200",
                ))

        return findings

    def _check_url_security(self, url: str) -> List[SecurityFinding]:
        findings = []
        parsed = urlparse(url)

        if parsed.scheme == "http":
            findings.append(SecurityFinding(
                id="url-001",
                title="Insecure Protocol (HTTP)",
                description="Request uses HTTP instead of HTTPS",
                severity=Severity.HIGH,
                category=Category.SSL_TLS,
                evidence={"scheme": parsed.scheme, "url": url},
                remediation="Use HTTPS for all communications.",
                cwe_id="CWE-319",
                owasp_ref="A02:2021-Cryptographic Failures",
            ))

        if "@" in parsed.netloc:
            findings.append(SecurityFinding(
                id="url-002",
                title="Credentials in URL",
                description="Username/password embedded in URL",
                severity=Severity.HIGH,
                category=Category.AUTHENTICATION,
                evidence={"netloc": parsed.netloc},
                remediation="Use headers or POST body for authentication, not URL credentials.",
                cwe_id="CWE-598",
            ))

        if parsed.query:
            params = parse_qs(parsed.query)
            if len(params) > 20:
                findings.append(SecurityFinding(
                    id="url-003",
                    title="Excessive URL Parameters",
                    description=f"URL contains {len(params)} parameters",
                    severity=Severity.INFO,
                    category=Category.INFORMATION,
                    evidence={"param_count": len(params)},
                    remediation="Consider using POST with JSON body for complex data.",
                ))

        return findings

    def _check_authentication(self, url: str, method: str, headers: Dict[str, str]) -> List[SecurityFinding]:
        findings = []
        auth_headers = [k for k in headers if "authorization" in k.lower()]

        if not auth_headers and method in ["POST", "PUT", "PATCH", "DELETE"]:
            findings.append(SecurityFinding(
                id="auth-002",
                title="Missing Authentication",
                description="State-changing request without Authorization header",
                severity=Severity.MEDIUM,
                category=Category.AUTHENTICATION,
                evidence={"method": method},
                remediation="Verify authentication is properly implemented for sensitive operations.",
                cwe_id="CWE-306",
            ))

        basic_auth = headers.get("authorization", "") + headers.get("Authorization", "")
        if basic_auth.startswith("Basic "):
            findings.append(SecurityFinding(
                id="auth-003",
                title="Basic Authentication Used",
                description="Request uses Basic authentication which transmits credentials in plain text",
                severity=Severity.HIGH,
                category=Category.AUTHENTICATION,
                evidence={"auth_type": "Basic"},
                remediation="Use Bearer tokens or OAuth instead.",
                cwe_id="CWE-318",
            ))

        return findings

    def _check_response_headers(self, headers: Dict[str, str]) -> List[SecurityFinding]:
        findings = []
        header_keys = {k.lower(): v for k, v in headers.items()}

        for header_name, config in self.INSECURE_HEADERS.items():
            if header_name not in header_keys:
                findings.append(SecurityFinding(
                    id=f"hdr-{header_name}",
                    title=f"Missing Security Header: {header_name}",
                    description=f"Response lacks the {header_name} security header",
                    severity=config["severity"],
                    category=Category.HEADERS,
                    evidence={"missing_header": header_name},
                    remediation=f"Add {header_name} header to response.",
                ))
            elif config["expected"]:
                value = header_keys[header_name].lower()
                if value not in [v.lower() for v in config["expected"]]:
                    findings.append(SecurityFinding(
                        id=f"hdr-{header_name}-invalid",
                        title=f"Weak Security Header: {header_name}",
                        description=f"{header_name} has weak value: {header_keys[header_name]}",
                        severity=config["severity"],
                        category=Category.HEADERS,
                        evidence={"header": header_name, "value": header_keys[header_name]},
                        remediation=f"Use stricter {header_name} value.",
                    ))

        return findings

    def _check_cors(self, headers: Dict[str, str]) -> List[SecurityFinding]:
        findings = []
        header_keys = {k.lower(): v for k, v in headers.items()}

        if "access-control-allow-origin" in header_keys:
            origin = header_keys["access-control-allow-origin"]
            if origin == "*":
                findings.append(SecurityFinding(
                    id="cors-001",
                    title="CORS Allows All Origins",
                    description="Access-Control-Allow-Origin is set to '*'",
                    severity=Severity.MEDIUM,
                    category=Category.CORS,
                    evidence={"allow-origin": origin},
                    remediation="Restrict CORS to specific trusted origins.",
                    cwe_id="CWE-942",
                ))

            if "access-control-allow-credentials" in header_keys:
                if header_keys["access-control-allow-credentials"].lower() == "true" and origin == "*":
                    findings.append(SecurityFinding(
                        id="cors-002",
                        title="CORS Wildcard with Credentials",
                        description="CORS allows credentials with wildcard origin",
                        severity=Severity.HIGH,
                        category=Category.CORS,
                        evidence={"origin": origin, "credentials": "true"},
                        remediation="Never use credentials with wildcard origin.",
                        cwe_id="CWE-942",
                    ))

        return findings

    def _check_sensitive_data_in_response(self, body: str) -> List[SecurityFinding]:
        findings = []

        for i, (pattern, desc, severity) in enumerate(self._sensitive_compiled):
            matches = pattern.findall(body)
            if matches:
                findings.append(SecurityFinding(
                    id=f"resp-sens-{i}",
                    title=f"Sensitive Data in Response: {desc}",
                    description="Response contains potentially sensitive information",
                    severity=severity,
                    category=Category.SENSITIVE_DATA,
                    evidence={"pattern_type": desc, "redacted": "[REDACTED]"},
                    remediation="Ensure response doesn't expose sensitive data unnecessarily.",
                    cwe_id="CWE-200",
                ))

        return findings

    def _check_error_disclosure(self, status_code: int, body: str) -> List[SecurityFinding]:
        findings = []

        error_codes = [400, 401, 403, 404, 500, 502, 503]
        if status_code in error_codes:
            error_keywords = ["exception", "stack trace", "error", "traceback", "sql", "mysql", "postgresql", "oracle"]
            body_lower = body.lower()
            found_keywords = [kw for kw in error_keywords if kw in body_lower]

            if found_keywords:
                findings.append(SecurityFinding(
                    id="err-001",
                    title="Verbose Error Message",
                    description=f"Status {status_code} response contains error details: {', '.join(found_keywords)}",
                    severity=Severity.MEDIUM,
                    category=Category.INFORMATION,
                    evidence={"status_code": status_code, "keywords": found_keywords},
                    remediation="Use generic error messages in production.",
                    cwe_id="CWE-209",
                ))

        if status_code == 500 and not found_keywords:
            findings.append(SecurityFinding(
                id="err-002",
                title="Internal Server Error",
                description="Server returned 500 without detailed error information",
                severity=Severity.INFO,
                category=Category.INFORMATION,
                evidence={"status_code": status_code},
                remediation="Ensure errors are logged server-side but not exposed to clients.",
            ))

        return findings

    def _check_cache_headers(self, headers: Dict[str, str]) -> List[SecurityFinding]:
        findings = []
        header_keys = {k.lower(): v for k, v in headers.items()}

        cache_sensitive = ["token", "auth", "credential", "session", "user", "profile"]
        content_type = header_keys.get("content-type", "")
        cache_control = header_keys.get("cache-control", "")

        if "private" not in cache_control.lower() and "no-store" not in cache_control.lower():
            for keyword in cache_sensitive:
                if keyword in content_type.lower():
                    findings.append(SecurityFinding(
                        id="cache-001",
                        title="Sensitive Data May Be Cached",
                        description=f"Content-Type suggests sensitive data but Cache-Control doesn't prevent caching",
                        severity=Severity.MEDIUM,
                        category=Category.HEADERS,
                        evidence={"content_type": content_type, "cache_control": cache_control},
                        remediation="Add Cache-Control: private, no-store for sensitive responses.",
                        cwe_id="CWE-524",
                    ))
                    break

        return findings

    def _calculate_risk_score(self, findings: List[SecurityFinding]) -> float:
        weights = {
            Severity.CRITICAL: 10.0,
            Severity.HIGH: 7.5,
            Severity.MEDIUM: 5.0,
            Severity.LOW: 2.5,
            Severity.INFO: 0.0,
        }

        total = sum(weights[f.severity] for f in findings)
        return min(100.0, total)


def get_risk_level(score: float) -> str:
    if score >= 75:
        return "Critical"
    elif score >= 50:
        return "High"
    elif score >= 25:
        return "Medium"
    elif score >= 10:
        return "Low"
    return "Informational"
