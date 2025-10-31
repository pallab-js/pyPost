# Project Structure

```
pyPost/
??? .gitignore              # Git ignore rules
??? LICENSE                 # MIT License
??? README.md               # Main documentation
??? CHANGELOG.md            # Version history
??? requirements.txt        # Python dependencies
?
??? main.py                 # Application entry point
??? main_window.py          # Main application window
??? request_tab.py          # Request tab widget
??? http_worker.py          # HTTP request worker thread
??? database.py             # Database management
??? environments_dialog.py  # Environment variables dialog
??? syntax_highlighter.py   # Syntax highlighting for responses
??? constants.py            # Application constants
?
??? test_main.py            # Tests for main.py
??? test_main_window.py     # Tests for main window
??? test_request_tab.py     # Tests for request tab
??? test_http.py            # Tests for HTTP worker
??? test_database.py        # Tests for database
??? test_environments_dialog.py  # Tests for environments
??? test_syntax_highlighter.py   # Tests for syntax highlighter
?
??? pypost.db               # SQLite database (user data, gitignored)
??? .encryption_key         # Encryption key (gitignored)
??? venv/                   # Virtual environment (gitignored)
```

## File Descriptions

### Core Application
- **main.py**: Application entry point, initializes QApplication
- **main_window.py**: Main window UI, manages tabs, collections, history
- **request_tab.py**: Individual request tabs with request/response UI
- **http_worker.py**: Thread worker for async HTTP requests
- **database.py**: SQLite database operations and encryption
- **environments_dialog.py**: Dialog for managing environment variables
- **syntax_highlighter.py**: Syntax highlighting for JSON/XML responses
- **constants.py**: Application constants (HTTP methods, auth types, etc.)

### Tests
All test files follow `test_*.py` naming convention and use pytest.

### Configuration
- **.gitignore**: Excludes venv, cache, database files, encryption keys
- **requirements.txt**: Python package dependencies
- **LICENSE**: MIT License
- **README.md**: User documentation
- **CHANGELOG.md**: Version history and changes

### User Data (Gitignored)
- **pypost.db**: SQLite database with collections, history, environments
- **.encryption_key**: Fernet encryption key for sensitive data
