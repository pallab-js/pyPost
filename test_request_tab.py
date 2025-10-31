import pytest
from unittest.mock import Mock, patch, MagicMock
from request_tab import RequestTab


@pytest.fixture
def db_manager_mock():
    return Mock()


@pytest.fixture
def request_tab(db_manager_mock):
    with patch('request_tab.DatabaseManager', return_value=db_manager_mock):
        tab = RequestTab(db_manager_mock)
        yield tab


def test_request_tab_init(request_tab, db_manager_mock):
    """Test RequestTab initialization"""
    assert request_tab.db_manager == db_manager_mock
    assert request_tab.current_environment == "Default"
    assert hasattr(request_tab, 'url_input')
    assert hasattr(request_tab, 'method_selector')
    assert hasattr(request_tab, 'send_button')


def test_get_headers(request_tab):
    """Test getting headers from table"""
    # Mock table items
    mock_item1 = Mock()
    mock_item1.text.return_value = "Content-Type"
    mock_item2 = Mock()
    mock_item2.text.return_value = "application/json"

    request_tab.headers_table.item.side_effect = lambda row, col: [mock_item1, mock_item2][col]
    request_tab.headers_table.rowCount.return_value = 1

    headers = request_tab.get_headers()
    assert headers == {"Content-Type": "application/json"}


def test_get_params(request_tab):
    """Test getting params from table"""
    mock_key = Mock()
    mock_key.text.return_value = "key"
    mock_value = Mock()
    mock_value.text.return_value = "value"

    request_tab.params_table.item.side_effect = lambda row, col: [mock_key, mock_value][col]
    request_tab.params_table.rowCount.return_value = 1

    params = request_tab.get_params()
    assert params == {"key": "value"}


def test_get_body_data(request_tab):
    """Test getting body data"""
    request_tab.body_type.currentText.return_value = "JSON"
    request_tab.body_input.toPlainText.return_value = '{"test": "data"}'

    body = request_tab.get_body_data()
    assert body == '{"test": "data"}'


def test_get_body_data_none(request_tab):
    """Test getting body data when none"""
    request_tab.body_type.currentText.return_value = "None"

    body = request_tab.get_body_data()
    assert body is None


def test_get_body_data_empty(request_tab):
    """Test getting body data when empty"""
    request_tab.body_type.currentText.return_value = "JSON"
    request_tab.body_input.toPlainText.return_value = ""

    body = request_tab.get_body_data()
    assert body is None


@patch('request_tab.json.loads')
@patch('request_tab.QMessageBox')
def test_send_request_invalid_json(mock_msgbox, mock_json, request_tab):
    """Test sending request with invalid JSON"""
    request_tab.body_type.currentText.return_value = "JSON"
    request_tab.body_input.toPlainText.return_value = "invalid json"
    request_tab.url_input.text.return_value = "https://example.com"
    request_tab.method_selector.currentText.return_value = "POST"
    mock_json.side_effect = ValueError("Invalid JSON")

    request_tab.send_request()

    mock_msgbox.warning.assert_called_once()


@patch('request_tab.QMessageBox')
def test_send_request_no_url(mock_msgbox, request_tab):
    """Test sending request without URL"""
    request_tab.url_input.text.return_value = ""

    request_tab.send_request()

    mock_msgbox.warning.assert_called_once_with(request_tab, "Error", "Please enter a URL")


@patch('request_tab.QMessageBox')
def test_send_request_invalid_url(mock_msgbox, request_tab):
    """Test sending request with invalid URL"""
    request_tab.url_input.text.return_value = "not-a-url"

    request_tab.send_request()

    mock_msgbox.warning.assert_called_once()


@patch('request_tab.HTTPWorker')
def test_send_request_success(mock_worker, request_tab, db_manager_mock):
    """Test successful request send"""
    request_tab.url_input.text.return_value = "https://example.com"
    request_tab.method_selector.currentText.return_value = "GET"
    request_tab.ssl_verify_checkbox.isChecked.return_value = True

    # Mock tables empty
    request_tab.headers_table.rowCount.return_value = 0
    request_tab.params_table.rowCount.return_value = 0
    request_tab.body_type.currentText.return_value = "None"

    request_tab.send_request()

    mock_worker.assert_called_once()
    # Check that worker is started
    mock_worker.return_value.start.assert_called_once()


def test_get_request_data(request_tab):
    """Test getting request data"""
    request_tab.method_selector.currentText.return_value = "GET"
    request_tab.url_input.text.return_value = "https://example.com"
    request_tab.auth_type.currentText.return_value = "No Auth"
    request_tab.body_type.currentText.return_value = "None"

    # Mock empty tables
    request_tab.headers_table.rowCount.return_value = 0
    request_tab.params_table.rowCount.return_value = 0

    data = request_tab.get_request_data()

    assert data['method'] == "GET"
    assert data['url'] == "https://example.com"


def test_get_request_data_with_auth(request_tab, db_manager_mock):
    """Test getting request data with auth"""
    request_tab.method_selector.currentText.return_value = "GET"
    request_tab.url_input.text.return_value = "https://example.com"
    request_tab.auth_type.currentText.return_value = "Bearer Token"
    request_tab.bearer_token_input.text.return_value = "token123"
    request_tab.body_type.currentText.return_value = "None"

    # Mock empty tables
    request_tab.headers_table.rowCount.return_value = 0
    request_tab.params_table.rowCount.return_value = 0

    db_manager_mock.encrypt.return_value = "encrypted_token"

    data = request_tab.get_request_data()

    db_manager_mock.encrypt.assert_called_once_with("token123")
    assert data['bearer_token'] == "encrypted_token"


def test_load_request_data(request_tab, db_manager_mock):
    """Test loading request data"""
    request_data = {
        'method': 'POST',
        'url': 'https://example.com',
        'auth_type': 'Bearer Token',
        'bearer_token': 'encrypted_token',
        'body_type': 'JSON',
        'body': '{"test": "data"}'
    }

    db_manager_mock.decrypt.return_value = "decrypted_token"

    request_tab.load_request_data(request_data)

    assert request_tab.method_selector.currentText() == "POST"
    assert request_tab.url_input.text() == "https://example.com"
    assert request_tab.auth_type.currentText() == "Bearer Token"
    assert request_tab.bearer_token_input.text() == "decrypted_token"
    assert request_tab.body_type.currentText() == "JSON"
    assert request_tab.body_input.toPlainText() == '{"test": "data"}'


def test_apply_substitutions(request_tab, db_manager_mock):
    """Test applying environment substitutions"""
    request_tab._get_env_variables.return_value = {"{{API_URL}}": "https://api.example.com"}

    url = "https://{{API_URL}}/endpoint"
    headers = {"Authorization": "Bearer {{API_URL}}"}
    params = {"url": "{{API_URL}}"}
    data = '{"base": "{{API_URL}}"}'

    result_url, result_headers, result_params, result_data = request_tab.apply_substitutions(url, headers, params, data)

    assert result_url == "https://api.example.com/endpoint"
    assert result_headers == {"Authorization": "Bearer https://api.example.com"}
    assert result_params == {"url": "https://api.example.com"}
    assert result_data == '{"base": "https://api.example.com"}'


def test_substitute_variables(request_tab):
    """Test substituting variables in UI"""
    request_tab._get_env_variables.return_value = {"{{NAME}}": "John"}

    # Mock table items
    mock_key = Mock()
    mock_key.text.return_value = "greeting"
    mock_value = Mock()
    mock_value.text.return_value = "Hello {{NAME}}"

    request_tab.params_table.rowCount.return_value = 1
    request_tab.params_table.item.side_effect = lambda row, col: [mock_key, mock_value][col]

    request_tab.url_input.text.return_value = "https://example.com/{{NAME}}"
    request_tab.body_input.toPlainText.return_value = '{"name": "{{NAME}}"}'

    request_tab.substitute_variables()

    assert request_tab.url_input.text() == "https://example.com/John"
    mock_value.setText.assert_called_once_with("Hello John")


def test_add_remove_param_row(request_tab):
    """Test adding and removing param rows"""
    initial_rows = request_tab.params_table.rowCount.return_value = 0

    request_tab.add_param_row()
    request_tab.params_table.insertRow.assert_called_once_with(0)

    request_tab.params_table.currentRow.return_value = 0
    request_tab.remove_param_row()
    request_tab.params_table.removeRow.assert_called_once_with(0)


def test_add_remove_header_row(request_tab):
    """Test adding and removing header rows"""
    request_tab.add_header_row()
    request_tab.headers_table.insertRow.assert_called_once_with(0)

    request_tab.headers_table.currentRow.return_value = 0
    request_tab.remove_header_row()
    request_tab.headers_table.removeRow.assert_called_once_with(0)


def test_add_remove_multipart_row(request_tab):
    """Test adding and removing multipart rows"""
    request_tab.add_multipart_row()
    request_tab.multipart_table.insertRow.assert_called_once_with(0)

    request_tab.multipart_table.currentRow.return_value = 0
    request_tab.remove_multipart_row()
    request_tab.multipart_table.removeRow.assert_called_once_with(0)


def test_get_files(request_tab):
    """Test getting files from multipart table"""
    mock_key = Mock()
    mock_key.text.return_value = "file1"
    mock_value = Mock()
    mock_value.text.return_value = "/path/to/file1"

    request_tab.multipart_table.rowCount.return_value = 1
    request_tab.multipart_table.item.side_effect = lambda row, col: [mock_key, mock_value][col]

    files = request_tab.get_files()
    assert files == {"file1": "/path/to/file1"}


def test_update_auth_ui(request_tab):
    """Test updating auth UI"""
    request_tab.update_auth_ui("Bearer Token")
    request_tab.bearer_token_input.show.assert_called_once()
    request_tab.basic_username.hide.assert_called_once()
    request_tab.basic_password.hide.assert_called_once()

    request_tab.update_auth_ui("Basic Auth")
    request_tab.bearer_token_input.hide.assert_called_once()
    request_tab.basic_username.show.assert_called_once()
    request_tab.basic_password.show.assert_called_once()


def test_update_body_ui(request_tab):
    """Test updating body UI"""
    request_tab.update_body_ui("Multipart Form-Data")
    request_tab.body_input.hide.assert_called_once()
    request_tab.multipart_table.show.assert_called_once()

    request_tab.update_body_ui("JSON")
    request_tab.body_input.show.assert_called_once()
    request_tab.multipart_table.hide.assert_called_once()