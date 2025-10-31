import pytest
import os
from unittest.mock import Mock, patch, mock_open
from http_worker import HTTPWorker


@pytest.fixture
def http_worker():
    return HTTPWorker('GET', 'https://httpbin.org/get', {}, None, None, True)


@pytest.fixture
def http_worker_with_data():
    return HTTPWorker('POST', 'https://httpbin.org/post', {'Content-Type': 'application/json'}, '{"key": "value"}', {'param': 'value'}, False)


@pytest.fixture
def http_worker_with_files():
    return HTTPWorker('POST', 'https://httpbin.org/post', {}, None, None, True, {'file': 'path/to/file'})


@patch('http_worker.requests.Session')
def test_http_worker_success(mock_session_class, http_worker):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_response.cookies = {}
    mock_response.text = '{"test": "data"}'
    mock_response.content = b'{"test": "data"}'
    
    mock_session = Mock()
    mock_session.request.return_value = mock_response
    mock_session_class.return_value = mock_session

    http_worker.finished = Mock()
    http_worker.error = Mock()

    http_worker.run()

    http_worker.finished.emit.assert_called_once()
    result = http_worker.finished.emit.call_args[0][0]
    assert result['status_code'] == 200
    assert result['text'] == '{"test": "data"}'
    assert result['size'] == len(b'{"test": "data"}')
    http_worker.error.emit.assert_not_called()


@patch('http_worker.requests.Session')
def test_http_worker_with_data(mock_session_class, http_worker_with_data):
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_response.cookies = {'session': 'abc'}
    mock_response.text = '{"created": true}'
    mock_response.content = b'{"created": true}'
    
    mock_session = Mock()
    mock_session.request.return_value = mock_response
    mock_session_class.return_value = mock_session

    http_worker_with_data.finished = Mock()
    http_worker_with_data.error = Mock()

    http_worker_with_data.run()

    mock_session.request.assert_called_once_with(
        method='POST',
        url='https://httpbin.org/post',
        headers={'Content-Type': 'application/json'},
        data='{"key": "value"}',
        params={'param': 'value'},
        files=None,
        timeout=30,
        verify=False
    )

    http_worker_with_data.finished.emit.assert_called_once()
    result = http_worker_with_data.finished.emit.call_args[0][0]
    assert result['status_code'] == 201
    assert 'session' in result['cookies']


@patch('http_worker.open', create=True)
@patch('http_worker.os.path.isfile')
@patch('http_worker.os.path.exists')
@patch('http_worker.requests.Session')
def test_http_worker_with_files(mock_session_class, mock_exists, mock_isfile, mock_open, http_worker_with_files):
    # Setup file mocks
    mock_exists.return_value = True
    mock_isfile.return_value = True
    mock_file = Mock()
    mock_file.read.return_value = b'file content'
    mock_open.return_value = mock_file
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.cookies = {}
    mock_response.text = 'File uploaded'
    mock_response.content = b'File uploaded'
    
    mock_session = Mock()
    mock_session.request.return_value = mock_response
    mock_session_class.return_value = mock_session

    http_worker_with_files.finished = Mock()
    http_worker_with_files.error = Mock()

    http_worker_with_files.run()

    # Check that file was opened
    mock_open.assert_called()
    # Check that session.request was called with files
    call_args = mock_session.request.call_args
    assert call_args is not None
    assert call_args[1]['files'] is not None

    http_worker_with_files.finished.emit.assert_called_once()


@patch('http_worker.requests.Session')
def test_http_worker_error(mock_session_class, http_worker):
    import requests
    mock_session = Mock()
    mock_session.request.side_effect = requests.exceptions.RequestException("Network error")
    mock_session_class.return_value = mock_session

    http_worker.finished = Mock()
    http_worker.error = Mock()

    http_worker.run()

    http_worker.error.emit.assert_called_once()
    assert "Network error" in http_worker.error.emit.call_args[0][0]
    http_worker.finished.emit.assert_not_called()


@patch('http_worker.requests.Session')
def test_http_worker_timeout_error(mock_session_class, http_worker):
    import requests
    mock_session = Mock()
    mock_session.request.side_effect = requests.exceptions.Timeout("Request timed out")
    mock_session_class.return_value = mock_session

    http_worker.finished = Mock()
    http_worker.error = Mock()

    http_worker.run()

    http_worker.error.emit.assert_called_once()
    assert "timed out" in http_worker.error.emit.call_args[0][0].lower()


@patch('http_worker.requests.Session')
def test_http_worker_connection_error(mock_session_class, http_worker):
    import requests
    mock_session = Mock()
    mock_session.request.side_effect = requests.exceptions.ConnectionError("Connection failed")
    mock_session_class.return_value = mock_session

    http_worker.finished = Mock()
    http_worker.error = Mock()

    http_worker.run()

    http_worker.error.emit.assert_called_once()
    assert "connection" in http_worker.error.emit.call_args[0][0].lower()


def test_http_worker_init(http_worker):
    """Test HTTPWorker initialization"""
    assert http_worker.method == 'GET'
    assert http_worker.url == 'https://httpbin.org/get'
    assert http_worker.headers == {}
    assert http_worker.data is None
    assert http_worker.params is None
    assert http_worker.verify is True
    assert http_worker.files is None


def test_http_worker_init_with_files(http_worker_with_files):
    """Test HTTPWorker initialization with files"""
    assert http_worker_with_files.files == {'file': 'path/to/file'}