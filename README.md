# pyPost - API Testing Tool

A fast, intuitive, and extensible open-source API testing tool for developers, built with Python and PySide6. It's a local-first, high-performance alternative to tools like Postman.

## Features

- **Request Composer**: Build HTTP requests with support for all major methods (GET, POST, PUT, PATCH, DELETE, etc.)
- **Response Viewer**: View responses with syntax highlighting, headers, and timing information
  - Automatic JSON/XML pretty-printing
  - Color-coded status codes (green/orange/red)
  - Human-readable file sizes (KB, MB, GB)
- **File Uploads**: Full support for multipart file uploads
- **Request Cancellation**: Cancel ongoing requests with dedicated cancel button
- **Collections**: Organize requests in hierarchical collections
- **History**: Track all your requests with automatic logging
  - Double-click to reload previous requests
- **Environments**: Use variables in requests for different environments
- **Authentication**: Support for Bearer Token and Basic Auth (encrypted storage)
- **SSL Verification**: Toggle SSL certificate verification for testing
- **Dark Mode**: Persistent dark mode preference
- **Local-First**: All data stored locally in SQLite database
- **Testing**: Comprehensive unit tests with pytest

## Installation

1. Install Python 3.10 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## Usage

1. **Creating Requests**: Use the URL bar to enter your endpoint and select the HTTP method
2. **Adding Parameters**: Use the Params tab to add query parameters (use Add/Remove Row buttons)
3. **Setting Headers**: Use the Headers tab to add custom headers (use Add/Remove Row buttons)
4. **Authentication**: Use the Authorization tab for Bearer token or Basic Auth
5. **SSL Verification**: Check/uncheck "Verify SSL" for certificate validation
6. **Request Body**: Use the Body tab for POST/PUT requests with JSON, XML, plain text, or multipart form-data
7. **File Uploads**: Select "Multipart Form-Data" in Body tab, then add files using "Add File" button
8. **Cancelling Requests**: Click "Cancel" button (appears during request) to stop ongoing requests
9. **Saving Requests**: Use File > Save Request to save requests to collections
10. **Reloading History**: Double-click any history entry to reload that request
11. **Managing Environments**: Click "Manage Environments" to create environment variables
12. **Dark Mode**: Toggle in View menu - preference is saved automatically
13. **Import/Export Collections**: Use File > Import/Export Collections for backup/sharing
14. **Running Tests**: Run `pytest` to execute unit tests

## Environment Variables

Use the format `{{variable_name}}` in your requests to substitute environment variables. For example:
- URL: `https://api.example.com/{{version}}/users`
- Header: `Authorization: Bearer {{api_token}}`

## Architecture

pyPost consists of the following components:

- **Main Window**: The primary GUI, managing tabs, collections, and history.
- **Request Tab**: Individual tabs for composing and sending HTTP requests.
- **Database Manager**: Handles SQLite database operations for persistence.
- **HTTP Worker**: Threaded worker for sending requests asynchronously.
- **Environments Dialog**: Manages environment variables.
- **Syntax Highlighter**: Provides syntax highlighting for responses.

## Security

- Sensitive data (Bearer tokens, Basic Auth credentials) are encrypted using Fernet symmetric encryption.
- Encryption key is generated on first run and stored locally in `.encryption_key`.
- SSL verification is enabled by default; disable only for testing.
- Input validation prevents malformed URLs and JSON bodies.
- No data is sent to external servers; all data remains local.
- **Warning**: Deleting `.encryption_key` will require re-entering credentials, as existing encrypted data cannot be decrypted.

## Troubleshooting

- **App won't start**: Ensure Python 3.10+ and dependencies are installed. Run `pip install -r requirements.txt`.
- **Requests fail**: Check URL format, SSL settings, and network connectivity. View logs in console.
- **Encryption errors**: If `.encryption_key` is corrupted, delete it to regenerate (note: existing encrypted data will be lost).
- **Syntax highlighting not working**: Install Pygments: `pip install pygments`.
- **UI issues**: Ensure PySide6 is properly installed and compatible with your system.

## Requirements

- Python 3.10+
- PySide6
- requests
- pygments (optional, for syntax highlighting)
- pytest (for testing)
- cryptography (for security features)

## License

This project is open source and available under the MIT License.