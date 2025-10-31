import json
import logging
from typing import Dict, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QTextEdit, QLabel, QGroupBox, QMessageBox, QComboBox, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence

from database import DatabaseManager
from http_worker import HTTPWorker
from syntax_highlighter import SyntaxHighlighter
from constants import *


class RequestTab(QWidget):
    """Individual request tab widget"""

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.http_worker = None
        self.current_environment = "Default"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # URL Bar
        url_layout = QHBoxLayout()
        self.method_selector = QComboBox()
        self.method_selector.addItems(HTTP_METHODS)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL or paste text")
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_request)

        # Cancel button (initially hidden)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_request)
        self.cancel_button.setEnabled(False)
        self.cancel_button.hide()

        # Keyboard shortcut for send
        self.send_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.send_shortcut.activated.connect(self.send_request)

        url_layout.addWidget(self.method_selector)
        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.send_button)
        url_layout.addWidget(self.cancel_button)

        # SSL verification checkbox
        self.ssl_verify_checkbox = QCheckBox("Verify SSL")
        self.ssl_verify_checkbox.setChecked(True)

        # Request Details Tabs
        self.request_tabs = QTabWidget()

        # Params tab
        params_widget = QWidget()
        params_layout = QVBoxLayout()
        self.params_table = QTableWidget()
        self.params_table.setColumnCount(2)
        self.params_table.setHorizontalHeaderLabels(['Key', 'Value'])
        self.params_table.horizontalHeader().setStretchLastSection(True)
        params_layout.addWidget(self.params_table)

        params_btn_layout = QHBoxLayout()
        add_param_btn = QPushButton("Add Row")
        add_param_btn.clicked.connect(self.add_param_row)
        remove_param_btn = QPushButton("Remove Row")
        remove_param_btn.clicked.connect(self.remove_param_row)
        params_btn_layout.addWidget(add_param_btn)
        params_btn_layout.addWidget(remove_param_btn)
        params_btn_layout.addStretch()
        params_layout.addLayout(params_btn_layout)

        params_widget.setLayout(params_layout)
        self.request_tabs.addTab(params_widget, "Params")

        # Headers tab
        headers_widget = QWidget()
        headers_layout = QVBoxLayout()
        self.headers_table = QTableWidget()
        self.headers_table.setColumnCount(2)
        self.headers_table.setHorizontalHeaderLabels(['Key', 'Value'])
        self.headers_table.horizontalHeader().setStretchLastSection(True)
        headers_layout.addWidget(self.headers_table)

        headers_btn_layout = QHBoxLayout()
        add_header_btn = QPushButton("Add Row")
        add_header_btn.clicked.connect(self.add_header_row)
        remove_header_btn = QPushButton("Remove Row")
        remove_header_btn.clicked.connect(self.remove_header_row)
        headers_btn_layout.addWidget(add_header_btn)
        headers_btn_layout.addWidget(remove_header_btn)
        headers_btn_layout.addStretch()
        headers_layout.addLayout(headers_btn_layout)

        headers_widget.setLayout(headers_layout)
        self.request_tabs.addTab(headers_widget, "Headers")

        # Authorization tab
        auth_widget = QWidget()
        auth_layout = QVBoxLayout()
        self.auth_type = QComboBox()
        self.auth_type.addItems(AUTH_TYPES)
        self.auth_type.currentTextChanged.connect(self.update_auth_ui)
        self.bearer_token_input = QLineEdit()
        self.bearer_token_input.setPlaceholderText("Enter Bearer Token")
        self.bearer_token_input.hide()

        self.basic_username = QLineEdit()
        self.basic_username.setPlaceholderText("Username")
        self.basic_username.hide()
        self.basic_password = QLineEdit()
        self.basic_password.setPlaceholderText("Password")
        self.basic_password.setEchoMode(QLineEdit.Password)
        self.basic_password.hide()

        auth_layout.addWidget(QLabel("Type:"))
        auth_layout.addWidget(self.auth_type)
        auth_layout.addWidget(QLabel("Token:"))
        auth_layout.addWidget(self.bearer_token_input)
        auth_layout.addWidget(QLabel("Username:"))
        auth_layout.addWidget(self.basic_username)
        auth_layout.addWidget(QLabel("Password:"))
        auth_layout.addWidget(self.basic_password)
        auth_layout.addStretch()
        auth_widget.setLayout(auth_layout)
        self.request_tabs.addTab(auth_widget, "Authorization")

        # Body tab
        body_widget = QWidget()
        body_layout = QVBoxLayout()
        self.body_type = QComboBox()
        self.body_type.addItems(BODY_TYPES)
        self.body_type.currentTextChanged.connect(self.update_body_ui)
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText("Enter request body")

        # Multipart table
        self.multipart_table = QTableWidget()
        self.multipart_table.setColumnCount(2)
        self.multipart_table.setHorizontalHeaderLabels(['Key', 'File Path'])
        self.multipart_table.horizontalHeader().setStretchLastSection(True)
        self.multipart_table.hide()

        multipart_btn_layout = QHBoxLayout()
        add_multipart_btn = QPushButton("Add File")
        add_multipart_btn.clicked.connect(self.add_multipart_row)
        remove_multipart_btn = QPushButton("Remove File")
        remove_multipart_btn.clicked.connect(self.remove_multipart_row)
        multipart_btn_layout.addWidget(add_multipart_btn)
        multipart_btn_layout.addWidget(remove_multipart_btn)
        multipart_btn_layout.addStretch()

        body_layout.addWidget(QLabel("Content Type:"))
        body_layout.addWidget(self.body_type)
        body_layout.addWidget(QLabel("Body:"))
        body_layout.addWidget(self.body_input)
        body_layout.addWidget(self.multipart_table)
        body_layout.addLayout(multipart_btn_layout)
        body_widget.setLayout(body_layout)
        self.request_tabs.addTab(body_widget, "Body")

        # Response section
        response_group = QGroupBox("Response")
        response_layout = QVBoxLayout()

        # Response metadata
        metadata_layout = QHBoxLayout()
        self.status_label = QLabel("Status: -")
        self.status_label.setTextFormat(Qt.RichText)  # Enable HTML formatting
        self.time_label = QLabel("Time: -")
        self.size_label = QLabel("Size: -")
        metadata_layout.addWidget(self.status_label)
        metadata_layout.addWidget(self.time_label)
        metadata_layout.addWidget(self.size_label)
        metadata_layout.addStretch()

        # Response tabs
        self.response_tabs = QTabWidget()

        # Response body tab
        self.response_body = QTextEdit()
        self.response_body.setReadOnly(True)
        self.response_highlighter = SyntaxHighlighter(self.response_body.document())
        self.response_tabs.addTab(self.response_body, "Body")

        # Response headers tab
        self.response_headers_table = QTableWidget()
        self.response_headers_table.setColumnCount(2)
        self.response_headers_table.setHorizontalHeaderLabels(['Key', 'Value'])
        self.response_headers_table.horizontalHeader().setStretchLastSection(True)
        self.response_tabs.addTab(self.response_headers_table, "Headers")

        # Response cookies tab
        self.response_cookies_table = QTableWidget()
        self.response_cookies_table.setColumnCount(2)
        self.response_cookies_table.setHorizontalHeaderLabels(['Key', 'Value'])
        self.response_cookies_table.horizontalHeader().setStretchLastSection(True)
        self.response_tabs.addTab(self.response_cookies_table, "Cookies")

        response_layout.addLayout(metadata_layout)
        response_layout.addWidget(self.response_tabs)
        response_group.setLayout(response_layout)

        layout.addLayout(url_layout)
        layout.addWidget(self.ssl_verify_checkbox)
        layout.addWidget(self.request_tabs)
        layout.addWidget(response_group)
        self.setLayout(layout)

    def _get_env_variables(self) -> Dict[str, str]:
        """Get environment variables as substitution dict"""
        env_id = None
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'env_selector'):
            main_window = main_window.parent()

        if not main_window:
            return {}

        for i in range(main_window.env_selector.count()):
            if main_window.env_selector.itemText(i) == self.current_environment:
                env_id = main_window.env_selector.itemData(i)
                break

        if not env_id:
            return {}

        variables = self.db_manager.execute_query(
            "SELECT name, value FROM environment_variables WHERE environment_id = ?",
            (env_id,)
        )
        return {f"{{{{{var['name']}}}}}": var['value'] for var in variables}

    def _substitute_text(self, text: str, substitutions: Dict[str, str]) -> str:
        """Apply environment variable substitutions to text"""
        for placeholder, value in substitutions.items():
            text = text.replace(placeholder, value)
        return text

    def update_auth_ui(self, auth_type: str):
        """Update authorization UI based on selected type"""
        if auth_type == AUTH_BEARER_TOKEN:
            self.bearer_token_input.show()
            self.basic_username.hide()
            self.basic_password.hide()
        elif auth_type == AUTH_BASIC:
            self.bearer_token_input.hide()
            self.basic_username.show()
            self.basic_password.show()
        else:
            self.bearer_token_input.hide()
            self.basic_username.hide()
            self.basic_password.hide()

    def update_body_ui(self, body_type: str):
        """Update body UI based on selected type"""
        if body_type == BODY_MULTIPART:
            self.body_input.hide()
            self.multipart_table.show()
        else:
            self.body_input.show()
            self.multipart_table.hide()

    def send_request(self):
        """Send HTTP request"""
        if self.http_worker and self.http_worker.isRunning():
            return

        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a URL")
            return

        # Validate URL structure
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL")
        except:
            QMessageBox.warning(self, "Error", "Please enter a valid URL")
            return

        # Validate JSON body if applicable
        body_type = self.body_type.currentText()
        if body_type == "JSON":
            body_text = self.body_input.toPlainText().strip()
            if body_text:
                try:
                    import json
                    json.loads(body_text)
                except json.JSONDecodeError:
                    QMessageBox.warning(self, "Error", "Invalid JSON in request body")
                    return

        # Validate files if multipart
        files = None
        if self.body_type.currentText() == BODY_MULTIPART:
            files = self.get_files()
            if files:
                # Validate that all files exist
                import os
                for key, file_path in files.items():
                    if not os.path.exists(file_path):
                        QMessageBox.warning(self, "File Error", f"File not found: {file_path}")
                        return
                    if not os.path.isfile(file_path):
                        QMessageBox.warning(self, "File Error", f"Path is not a file: {file_path}")
                        return

        # Prepare request data
        method = self.method_selector.currentText()
        headers = self.get_headers()
        params = self.get_params()
        data = self.get_body_data()

        # Apply environment variable substitutions
        if self.current_environment:
            url, headers, params, data = self.apply_substitutions(url, headers, params, data)

        # Start HTTP worker
        self.http_worker = HTTPWorker(method, url, headers, data, params, self.ssl_verify_checkbox.isChecked(), files)
        self.http_worker.finished.connect(self.handle_response)
        self.http_worker.error.connect(self.handle_error)
        self.http_worker.start()

        # Update UI
        self.send_button.setText("Sending...")
        self.send_button.setEnabled(False)
        self.cancel_button.show()
        self.cancel_button.setEnabled(True)

    def get_headers(self) -> Dict[str, str]:
        """Extract headers from headers table"""
        headers = {}
        for row in range(self.headers_table.rowCount()):
            key_item = self.headers_table.item(row, 0)
            value_item = self.headers_table.item(row, 1)
            if key_item and value_item and key_item.text().strip():
                headers[key_item.text().strip()] = value_item.text().strip()

        # Add authorization header
        auth_type = self.auth_type.currentText()
        if auth_type == "Bearer Token" and self.bearer_token_input.text().strip():
            headers['Authorization'] = f"Bearer {self.bearer_token_input.text().strip()}"
        elif auth_type == "Basic Auth" and self.basic_username.text().strip() and self.basic_password.text().strip():
            import base64
            creds = f"{self.basic_username.text().strip()}:{self.basic_password.text().strip()}"
            encoded = base64.b64encode(creds.encode()).decode()
            headers['Authorization'] = f"Basic {encoded}"

        return headers

    def get_params(self) -> Dict[str, str]:
        """Extract URL parameters from params table"""
        params = {}
        for row in range(self.params_table.rowCount()):
            key_item = self.params_table.item(row, 0)
            value_item = self.params_table.item(row, 1)
            if key_item and value_item and key_item.text().strip():
                params[key_item.text().strip()] = value_item.text().strip()
        return params

    def get_body_data(self) -> Optional[str]:
        """Get request body data"""
        body_type = self.body_type.currentText()
        if body_type == BODY_NONE:
            return None
        elif body_type == BODY_MULTIPART:
            # For multipart, return dict of files, but since requests expects files, handle in send_request
            return None

        body_text = self.body_input.toPlainText()
        if not body_text.strip():
            return None

        return body_text

    def get_files(self) -> Optional[Dict[str, str]]:
        """Get multipart files dict"""
        files = {}
        for row in range(self.multipart_table.rowCount()):
            key_item = self.multipart_table.item(row, 0)
            value_item = self.multipart_table.item(row, 1)
            if key_item and value_item and key_item.text().strip() and value_item.text().strip():
                files[key_item.text().strip()] = value_item.text().strip()
        return files if files else None

    def apply_substitutions(self, url: str, headers: Dict[str, str], params: Dict[str, str], data: Optional[str]):
        """Apply environment variable substitutions to request data"""
        substitutions = self._get_env_variables()
        if not substitutions:
            return url, headers, params, data

        url = self._substitute_text(url, substitutions)
        headers = {k: self._substitute_text(v, substitutions) for k, v in headers.items()}
        params = {k: self._substitute_text(v, substitutions) for k, v in params.items()}
        if data:
            data = self._substitute_text(data, substitutions)

        return url, headers, params, data

    def handle_response(self, result: Dict):
        """Handle successful HTTP response"""
        self.send_button.setText("Send")
        self.send_button.setEnabled(True)
        self.cancel_button.hide()
        self.cancel_button.setEnabled(False)

        # Format response size
        size = result.get('size', 0)
        size_str = self.format_size(size)

        # Update response metadata with color coding
        status_code = result.get('status_code', 0)
        status_text = f"Status: {status_code}"
        if 200 <= status_code < 300:
            status_color = "green"
        elif 400 <= status_code < 500:
            status_color = "orange"
        elif status_code >= 500:
            status_color = "red"
        else:
            status_color = "blue"
        
        self.status_label.setText(f'<span style="color: {status_color};">{status_text}</span>')
        response_time = result.get('response_time', 0)
        self.time_label.setText(f"Time: {response_time} ms")
        self.size_label.setText(f"Size: {size_str}")

        # Format and update response body
        content_type = result.get('headers', {}).get('Content-Type', '')
        response_text = result.get('text', '')
        formatted_body = self.format_response_body(response_text, content_type)
        self.response_body.setPlainText(formatted_body)
        
        # Set syntax highlighter based on content type
        if hasattr(self, 'response_highlighter') and self.response_highlighter:
            self.response_highlighter.set_lexer(content_type)

        # Update response headers
        headers = result.get('headers', {})
        self.response_headers_table.setRowCount(len(headers))
        for i, (key, value) in enumerate(headers.items()):
            self.response_headers_table.setItem(i, 0, QTableWidgetItem(str(key)))
            self.response_headers_table.setItem(i, 1, QTableWidgetItem(str(value)))

        # Update response cookies
        cookies = result.get('cookies', {})
        self.response_cookies_table.setRowCount(len(cookies))
        for i, (key, value) in enumerate(cookies.items()):
            self.response_cookies_table.setItem(i, 0, QTableWidgetItem(str(key)))
            self.response_cookies_table.setItem(i, 1, QTableWidgetItem(str(value)))

        # Log to history
        self.log_to_history(result)

    def handle_error(self, error_msg: str):
        """Handle HTTP request error"""
        self.send_button.setText("Send")
        self.send_button.setEnabled(True)
        self.cancel_button.hide()
        self.cancel_button.setEnabled(False)

        self.status_label.setText('<span style="color: red;">Status: Error</span>')
        self.time_label.setText("Time: -")
        self.size_label.setText("Size: -")
        self.response_body.setPlainText(f"Error: {error_msg}")

        QMessageBox.critical(self, "Request Error", f"Failed to send request:\n{error_msg}")
    
    def cancel_request(self):
        """Cancel ongoing request"""
        worker = self.http_worker  # Get reference to avoid race condition
        if worker and worker.isRunning():
            try:
                worker.cancel()
                # Wait a bit for the thread to stop gracefully
                if not worker.wait(1000):
                    # Force terminate if it doesn't stop gracefully
                    worker.terminate()
                    worker.wait()
            except Exception as e:
                logging.warning(f"Error cancelling request: {e}")
            finally:
                self.http_worker = None
        
        self.send_button.setText("Send")
        self.send_button.setEnabled(True)
        self.cancel_button.hide()
        self.cancel_button.setEnabled(False)
        
        self.status_label.setText('<span style="color: orange;">Status: Cancelled</span>')
    
    def format_size(self, size_bytes: int) -> str:
        """Format size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def format_response_body(self, text: str, content_type: str) -> str:
        """Format response body based on content type"""
        if not text or not isinstance(text, str):
            return str(text) if text is not None else ""
        
        content_type_lower = (content_type or "").lower()
        
        # Pretty print JSON
        if 'json' in content_type_lower or (not content_type and self._looks_like_json(text)):
            try:
                data = json.loads(text)
                return json.dumps(data, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, ValueError):
                return text  # Return as-is if invalid JSON
        
        # Pretty print XML
        elif 'xml' in content_type_lower or (not content_type and self._looks_like_xml(text)):
            try:
                import xml.dom.minidom
                dom = xml.dom.minidom.parseString(text)
                return dom.toprettyxml(indent="  ")
            except Exception:
                return text
        
        return text
    
    def _looks_like_json(self, text: str) -> bool:
        """Heuristic to check if text looks like JSON"""
        text_stripped = text.strip()
        return text_stripped.startswith(('{', '[')) and text_stripped.endswith(('}', ']'))
    
    def _looks_like_xml(self, text: str) -> bool:
        """Heuristic to check if text looks like XML"""
        text_stripped = text.strip()
        return text_stripped.startswith('<') and '>' in text_stripped

    def log_to_history(self, result: Dict):
        """Log request to history"""
        request_data = {
            'method': self.method_selector.currentText(),
            'url': self.url_input.text(),
            'headers': self.get_headers(),
            'params': self.get_params(),
            'body': self.get_body_data()
        }

        self.db_manager.execute_update(
            """INSERT INTO history (method, url, request_data, response_data, status_code, response_time)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                self.method_selector.currentText(),
                self.url_input.text(),
                json.dumps(request_data),
                json.dumps(result),
                result['status_code'],
                result['response_time']
            )
        )

    def get_request_data(self) -> Dict:
        """Get current request data as dictionary"""
        auth_type = self.auth_type.currentText()
        bearer_token = self.bearer_token_input.text() if auth_type == "Bearer Token" else None
        if bearer_token:
            bearer_token = self.db_manager.encrypt(bearer_token)
        basic_username = self.basic_username.text() if auth_type == "Basic Auth" else None
        if basic_username:
            basic_username = self.db_manager.encrypt(basic_username)
        basic_password = self.basic_password.text() if auth_type == "Basic Auth" else None
        if basic_password:
            basic_password = self.db_manager.encrypt(basic_password)

        return {
            'method': self.method_selector.currentText(),
            'url': self.url_input.text(),
            'headers': self.get_headers(),
            'params': self.get_params(),
            'body': self.get_body_data(),
            'auth_type': auth_type,
            'bearer_token': bearer_token,
            'basic_username': basic_username,
            'basic_password': basic_password,
            'body_type': self.body_type.currentText()
        }

    def load_request_data(self, request_data: Dict):
        """Load request data from dictionary"""
        self.method_selector.setCurrentText(request_data.get('method', 'GET'))
        self.url_input.setText(request_data.get('url', ''))

        # Load headers
        headers = request_data.get('headers', {})
        self.headers_table.setRowCount(len(headers))
        for i, (key, value) in enumerate(headers.items()):
            self.headers_table.setItem(i, 0, QTableWidgetItem(key))
            self.headers_table.setItem(i, 1, QTableWidgetItem(value))

        # Load params
        params = request_data.get('params', {})
        self.params_table.setRowCount(len(params))
        for i, (key, value) in enumerate(params.items()):
            self.params_table.setItem(i, 0, QTableWidgetItem(key))
            self.params_table.setItem(i, 1, QTableWidgetItem(value))

        # Load auth
        auth_type = request_data.get('auth_type', 'No Auth')
        self.auth_type.setCurrentText(auth_type)
        if auth_type == "Bearer Token":
            bearer_token = request_data.get('bearer_token')
            if bearer_token:
                try:
                    bearer_token = self.db_manager.decrypt(bearer_token)
                except Exception:
                    bearer_token = ''  # Decryption failed, perhaps old data
            self.bearer_token_input.setText(bearer_token or '')
        elif auth_type == "Basic Auth":
            basic_username = request_data.get('basic_username')
            if basic_username:
                try:
                    basic_username = self.db_manager.decrypt(basic_username)
                except Exception:
                    basic_username = ''
            self.basic_username.setText(basic_username or '')
            basic_password = request_data.get('basic_password')
            if basic_password:
                try:
                    basic_password = self.db_manager.decrypt(basic_password)
                except Exception:
                    basic_password = ''
            self.basic_password.setText(basic_password or '')

        # Load body
        body_type = request_data.get('body_type', 'None')
        self.body_type.setCurrentText(body_type)
        self.body_input.setPlainText(request_data.get('body', ''))

    def substitute_variables(self):
        """Substitute environment variables in request data"""
        substitutions = self._get_env_variables()
        if not substitutions:
            return

        # Apply to URL
        self.url_input.setText(self._substitute_text(self.url_input.text(), substitutions))

        # Apply to headers
        for row in range(self.headers_table.rowCount()):
            key_item = self.headers_table.item(row, 0)
            value_item = self.headers_table.item(row, 1)
            if key_item and value_item:
                value_item.setText(self._substitute_text(value_item.text(), substitutions))

        # Apply to params
        for row in range(self.params_table.rowCount()):
            key_item = self.params_table.item(row, 0)
            value_item = self.params_table.item(row, 1)
            if key_item and value_item:
                value_item.setText(self._substitute_text(value_item.text(), substitutions))

        # Apply to body
        self.body_input.setPlainText(self._substitute_text(self.body_input.toPlainText(), substitutions))

    def add_param_row(self):
        """Add a new row to params table"""
        row = self.params_table.rowCount()
        self.params_table.insertRow(row)

    def remove_param_row(self):
        """Remove selected row from params table"""
        current_row = self.params_table.currentRow()
        if current_row >= 0:
            self.params_table.removeRow(current_row)

    def add_header_row(self):
        """Add a new row to headers table"""
        row = self.headers_table.rowCount()
        self.headers_table.insertRow(row)

    def remove_header_row(self):
        """Remove selected row from headers table"""
        current_row = self.headers_table.currentRow()
        if current_row >= 0:
            self.headers_table.removeRow(current_row)

    def add_multipart_row(self):
        """Add a new row to multipart table with file selection"""
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            row = self.multipart_table.rowCount()
            self.multipart_table.insertRow(row)
            # Assume key is filename
            import os
            key = os.path.basename(file_path)
            self.multipart_table.setItem(row, 0, QTableWidgetItem(key))
            self.multipart_table.setItem(row, 1, QTableWidgetItem(file_path))

    def remove_multipart_row(self):
        """Remove selected row from multipart table"""
        current_row = self.multipart_table.currentRow()
        if current_row >= 0:
            self.multipart_table.removeRow(current_row)