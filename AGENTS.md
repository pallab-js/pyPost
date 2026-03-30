# pyPost Agent Guidelines

This file provides guidance for AI agents working in this codebase.

---

## Build, Lint, and Test Commands

### Running Tests

```bash
# Run all tests
python3 -m pytest

# Run all tests (quiet mode)
python3 -m pytest -q

# Run specific test file
python3 -m pytest test_assertions.py -v

# Run single test function
python3 -m pytest test_assertions.py::TestAssertionEngine::test_equals_assertion -v

# Run tests matching pattern
python3 -m pytest -k "test_security" -v

# Run with coverage
python3 -m pytest --cov=. --cov-report=term-missing

# Skip GUI tests (Qt-related tests that may crash)
python3 -m pytest --ignore=test_main_window.py --ignore=test_request_tab.py
```

### Linting and Formatting

```bash
# Format code with black (line length: 100)
black .

# Sort imports with isort
isort .

# Run both
isort . && black .

# Flake8 linting
flake8 .

# Type checking (if mypy installed)
mypy .
```

### CLI Commands

```bash
# Run collection
python3 cli/main.py run collection.json

# Security scan
python3 cli/main.py security-scan https://api.example.com

# Generate test data
python3 cli/main.py generate-data --template '{"name": "{{full_name}}"}' --count 5

# Audit logs
python3 cli/main.py audit-logs --days 30

# Mock server
python3 cli/main.py mock-server --port 5000

# Help
python3 cli/main.py --help
```

---

## Code Style Guidelines

### Python Version
- Minimum: Python 3.9
- Target: Python 3.9+

### Imports
- Standard library imports first
- Third-party imports second (PySide6, requests, etc.)
- Local imports third
- Separate groups with blank lines
- Use absolute imports for package modules

```python
# Correct
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import QMainWindow
from database import DatabaseManager
from core.assertions import AssertionEngine

# Avoid
import sys
from .extractors import BaseExtractor  # Relative imports discouraged
```

### Type Annotations
- Use type hints for function parameters and return values
- Use `Optional[X]` instead of `X | None`
- Use `Dict`, `List` from `typing` (not built-in `dict`, `list`)

```python
# Correct
def process_request(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    pass

# Avoid
def process_request(url, headers=None):
    # No type hints
    pass
```

### Naming Conventions
- Classes: `PascalCase` (e.g., `AssertionEngine`, `SecurityScanner`)
- Functions/methods: `snake_case` (e.g., `extract_value`, `run_collection`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- Variables: `snake_case` (e.g., `request_id`, `collection_name`)
- Private members: prefix with `_` (e.g., `_config`, `_plugins`)

### Dataclasses
- Use `@dataclass` for data structures
- Use `field(default_factory=...)` for mutable defaults
- Use `field(default=...)` for immutable defaults

```python
@dataclass
class SecurityFinding:
    id: str
    title: str
    severity: Severity
    category: Category
    evidence: Dict[str, Any] = field(default_factory=dict)
    remediation: str = ""
    cwe_id: Optional[str] = None
```

### Enums
- Use `Enum` for related constants
- Values should be lowercase with underscores (e.g., `SEVERITY_HIGH = "high"`)
- Prefer string values over int values for serialization

```python
class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
```

### Error Handling
- Use specific exception types when possible
- Catch exceptions at appropriate levels
- Include context in error messages
- Log errors with appropriate severity

```python
# Correct
try:
    with open(config_path) as f:
        config = json.load(f)
except json.JSONDecodeError as e:
    logging.error(f"Failed to parse config: {e}")
    return None
except FileNotFoundError:
    logging.warning(f"Config file not found: {config_path}")
    return {}

# Avoid
try:
    data = eval(text)  # NEVER use eval() - security risk!
except:
    pass
```

### Security
- **NEVER use `eval()` or `exec()`** - security vulnerability
- Use `json.loads()` for JSON parsing
- Sanitize user input before using in queries
- Use parameterized queries for database operations

### Documentation
- Use docstrings for public classes and functions
- Keep docstrings concise but informative
- Use triple quotes for docstrings

```python
class SecurityScanner:
    """Security vulnerability scanner for API requests and responses.
    
    Scans for SQL injection, XSS, sensitive data exposure,
    missing security headers, and other vulnerabilities.
    """
    
    def scan_request(self, url: str, method: str, headers: Dict[str, str]) -> SecurityReport:
        """Scan a request for security issues.
        
        Args:
            url: The request URL
            method: HTTP method (GET, POST, etc.)
            headers: Request headers
            
        Returns:
            SecurityReport with findings and risk score
        """
        pass
```

### Qt/PySide6 Conventions
- Qt enums accessed via class (e.g., `Qt.Horizontal`, not `Qt.Horizontal`)
- Use `isinstance(widget, SomeWidget)` for type checking
- GUI tests may crash in headless environments - skip if needed

### File Structure
```
Package/
├── __init__.py          # Exports, version
├── module.py            # Main module code
├── submodule/
│   ├── __init__.py
│   └── module.py
└── tests/
    └── test_module.py
```

### Testing Conventions
- Test files: `test_<module_name>.py`
- Test classes: `TestClassName`
- Test functions: `test_function_name`
- Use `pytest` fixtures for setup/teardown
- Tests should be independent and idempotent

```python
class TestSecurityScanner:
    def setup_method(self):
        """Called before each test method"""
        self.scanner = SecurityScanner()
    
    def test_detects_sql_injection(self):
        report = self.scanner.scan_request(
            "https://api.example.com",
            "GET",
            {},
            params={"id": "1 OR 1=1"},
        )
        assert report.high_count > 0
```

---

## Project Structure

```
pyPost/
├── core/           # Core features (GraphQL, WebSocket, Assertions, etc.)
├── engine/          # Engine modules (Mock Server, Runner, Code Gen)
├── adapters/        # Import/Export adapters (OpenAPI)
├── integrations/    # Third-party integrations (Git)
├── plugins/         # Plugin system
├── security/        # Security scanning
├── utils/           # Utilities (Data Generator)
├── cli/             # CLI interface
└── tests/           # Test files (test_*.py)
```

---

## Dependencies

Core dependencies are in `pyproject.toml`:
- PySide6 (GUI)
- requests (HTTP)
- cryptography (Security)
- pygments (Syntax highlighting)

Dev dependencies:
- pytest, pytest-cov, pytest-mock, pytest-qt
- black, isort, flake8
