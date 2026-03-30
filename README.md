# pyPost - Professional API Testing Workstation

A fast, intuitive, and extensible open-source API testing tool for developers, built with Python and PySide6. It's a local-first, high-performance alternative to tools like Postman, Swagger, Hoppscotch, and Apidog.

## Features

### Core Features
- **Multi-Protocol Support**: HTTP, HTTPS, GraphQL, WebSocket
- **Request Composer**: Build requests with all HTTP methods (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)
- **Response Viewer**: Syntax highlighting, JSON/XML pretty-printing, headers, timing
- **Collections**: Hierarchical organization of requests
- **History**: Automatic logging with double-click to reload
- **Environments**: Variable substitution with `{{variable}}` syntax
- **Authentication**: Bearer Token, Basic Auth, HMAC signing (encrypted storage)
- **SSL Verification**: Toggle for testing self-signed certificates
- **Dark Mode**: Persistent theme preference
- **Local-First**: All data stored in SQLite

### Professional Features
- **Assertion Engine**: Status code, JSONPath, Header, ResponseTime, BodyContains assertions
- **Request Chaining**: Extract values from responses to use in subsequent requests
- **Mock Server**: Flask-based local server with static responses and delay simulation
- **Collection Runner**: Sequential execution with reports (JSON, HTML, Markdown)
- **Code Generator**: cURL, Python, JavaScript, Java, PHP, Go
- **OpenAPI Support**: Import/export OpenAPI 3.x specifications

### Advanced Features
- **Security Scanner**: SQL injection, XSS, sensitive data exposure, missing headers, CORS
- **Plugin System**: Extensible architecture with pre/post request hooks
- **Git Integration**: Version control for collections
- **CLI Runner**: Headless execution for CI/CD
- **Test Data Generator**: 30+ data types with template syntax
- **Structured Logging**: SQLite-persisted request logs
- **Audit Logging**: Full activity tracking for compliance

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pyPost.git
cd pyPost

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Quick Start

1. **Create a Request**: Enter URL, select method, add headers/body
2. **Send**: Click Send or press Ctrl+Enter
3. **Save**: File > Save Request to store in collections
4. **Run Tests**: Tools > Security Scanner for vulnerability checks

## CLI Usage

```bash
# Run a collection
python cli/main.py run collection.json --env staging

# Security scan
python cli/main.py security-scan https://api.example.com -o report.json

# Generate test data
python cli/main.py generate-data --template '{"name": "{{full_name}}", "email": "{{email}}"}' --count 10

# Mock server
python cli/main.py mock-server --port 5000

# View audit logs
python cli/main.py audit-logs --days 30
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New Request |
| Ctrl+S | Save Request |
| Ctrl+Enter | Send Request |
| Ctrl+W | Close Tab |
| Ctrl+T | Request Templates |
| Ctrl+Shift+C | Compare Requests |
| Ctrl+Shift+E | Security Scanner |
| Ctrl+Shift+D | Data Generator |

## Architecture

```
pyPost/
├── core/           # Core runtime (GraphQL, WebSocket, Assertions, Chaining)
├── engine/          # Engine (Mock Server, Runner, Code Generator)
├── adapters/       # Import/Export (OpenAPI)
├── integrations/    # Git integration
├── plugins/        # Plugin system
├── security/        # Security scanner
├── utils/          # Utilities (Data Generator)
├── cli/            # CLI interface
└── tests/          # Unit tests (279 tests)
```

## Testing

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest test_security.py -v

# Run with coverage
python -m pytest --cov=. --cov-report=term-missing

# Skip GUI tests (headless environments)
python -m pytest --ignore=test_main_window.py
```

## Requirements

- Python 3.9+
- PySide6 6.5+ (GUI)
- requests 2.28+
- cryptography 41.0+ (security)
- pytest 7.0+ (testing)
- flask 2.0+ (mock server)
- websockets 10.0+ (WebSocket client)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
