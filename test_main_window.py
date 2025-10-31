import pytest
from unittest.mock import Mock, patch, MagicMock
from main_window import MainWindow


@pytest.fixture
def db_manager_mock():
    return Mock()


@pytest.fixture
def main_window(db_manager_mock):
    with patch('main_window.DatabaseManager', return_value=db_manager_mock):
        window = MainWindow()
        yield window


def test_main_window_init(main_window, db_manager_mock):
    """Test MainWindow initialization"""
    assert main_window.db_manager == db_manager_mock
    assert hasattr(main_window, 'sidebar')
    assert hasattr(main_window, 'main_panel')
    assert hasattr(main_window, 'request_tabs')


@patch('main_window.QMessageBox')
def test_add_request_tab(mock_msgbox, main_window):
    """Test adding request tab"""
    initial_count = main_window.request_tabs.count()
    main_window.add_request_tab()
    assert main_window.request_tabs.count() == initial_count + 1


@patch('main_window.QMessageBox')
def test_close_request_tab(mock_msgbox, main_window):
    """Test closing request tab"""
    main_window.add_request_tab()
    initial_count = main_window.request_tabs.count()
    main_window.close_request_tab(0)
    # Should not close if only one tab
    assert main_window.request_tabs.count() == initial_count


def test_close_request_tab_multiple(mock_msgbox, main_window):
    """Test closing request tab when multiple exist"""
    main_window.add_request_tab()
    main_window.add_request_tab()
    initial_count = main_window.request_tabs.count()
    main_window.close_request_tab(0)
    assert main_window.request_tabs.count() == initial_count - 1


@patch('main_window.QInputDialog')
@patch('main_window.QMessageBox')
def test_save_current_request(mock_input, mock_msgbox, main_window, db_manager_mock):
    """Test saving current request"""
    mock_input.getText.return_value = ("Test Request", True)
    db_manager_mock.execute_update.return_value = 1

    # Mock current tab
    mock_tab = Mock()
    mock_tab.get_request_data.return_value = {'url': 'https://example.com'}
    main_window.request_tabs.currentWidget.return_value = mock_tab

    main_window.save_current_request()

    db_manager_mock.execute_update.assert_called_once()
    mock_msgbox.information.assert_called_once()


@patch('main_window.QMessageBox')
def test_save_current_request_no_url(mock_msgbox, main_window):
    """Test saving request without URL"""
    mock_tab = Mock()
    mock_tab.get_request_data.return_value = {'url': ''}
    main_window.request_tabs.currentWidget.return_value = mock_tab

    main_window.save_current_request()

    mock_msgbox.warning.assert_called_once_with(main_window, "Error", "Please enter a URL to save")


@patch('main_window.QFileDialog')
@patch('main_window.QMessageBox')
def test_import_collections(mock_filedialog, mock_msgbox, main_window, db_manager_mock):
    """Test importing collections"""
    mock_filedialog.getOpenFileName.return_value = ("/path/to/file.json", "JSON Files (*.json)")
    mock_collections = [
        {"name": "Test Collection", "request_data": '{"method": "GET"}'}
    ]

    with patch('builtins.open', Mock()) as mock_open:
        with patch('json.load', return_value=mock_collections):
            main_window.import_collections()

    db_manager_mock.execute_update.assert_called_once()
    mock_msgbox.information.assert_called_once()


@patch('main_window.QFileDialog')
@patch('main_window.QMessageBox')
def test_export_collections(mock_filedialog, mock_msgbox, main_window, db_manager_mock):
    """Test exporting collections"""
    mock_filedialog.getSaveFileName.return_value = ("/path/to/file.json", "JSON Files (*.json)")
    db_manager_mock.execute_query.return_value = [
        {"name": "Test Collection", "request_data": '{"method": "GET"}'}
    ]

    with patch('builtins.open', Mock()) as mock_open:
        with patch('json.dump') as mock_dump:
            main_window.export_collections()

    mock_dump.assert_called_once()
    mock_msgbox.information.assert_called_once()


def test_load_environments(main_window, db_manager_mock):
    """Test loading environments"""
    db_manager_mock.execute_query.return_value = [
        {"id": 1, "name": "Default"},
        {"id": 2, "name": "Production"}
    ]

    main_window.load_environments()

    assert main_window.env_selector.count() == 2
    assert main_window.env_selector.itemText(0) == "Default"


def test_load_collections(main_window, db_manager_mock):
    """Test loading collections"""
    db_manager_mock.execute_query.return_value = [
        {"id": 1, "name": "Test Collection", "parent_id": None, "request_data": '{"method": "GET"}'}
    ]

    main_window.load_collections()

    # Check that model has items
    assert main_window.collections_model.rowCount() > 0


def test_load_history(main_window, db_manager_mock):
    """Test loading history"""
    db_manager_mock.execute_query.return_value = [
        {"id": 1, "method": "GET", "url": "https://example.com", "status_code": 200, "created_at": "2023-01-01"}
    ]

    main_window.load_history()

    assert main_window.history_list.count() == 1


@patch('main_window.QMessageBox')
def test_show_about(mock_msgbox, main_window):
    """Test showing about dialog"""
    main_window.show_about()

    mock_msgbox.about.assert_called_once()


@patch('main_window.QMessageBox')
def test_manage_environments(mock_msgbox, main_window):
    """Test managing environments"""
    mock_dialog = Mock()
    mock_dialog.exec.return_value = 1  # Accepted

    with patch('main_window.EnvironmentsDialog', return_value=mock_dialog):
        main_window.manage_environments()

    # Should reload environments
    assert main_window.load_environments.called


def test_on_environment_changed(main_window):
    """Test environment change handling"""
    # Add mock tabs
    mock_tab1 = Mock()
    mock_tab2 = Mock()
    main_window.request_tabs.widget.side_effect = [mock_tab1, mock_tab2]

    main_window.on_environment_changed("TestEnv")

    mock_tab1.current_environment = "TestEnv"
    mock_tab1.substitute_variables.assert_called_once()
    mock_tab2.current_environment = "TestEnv"
    mock_tab2.substitute_variables.assert_called_once()


@patch('main_window.QMessageBox')
def test_load_request_from_collection(mock_msgbox, main_window, db_manager_mock):
    """Test loading request from collection"""
    # Mock collection data
    mock_item = Mock()
    mock_item.data.return_value = {"request_data": '{"method": "GET", "url": "https://example.com"}'}
    main_window.collections_model.itemFromIndex.return_value = mock_item

    # Mock current tab
    mock_tab = Mock()
    main_window.request_tabs.currentWidget.return_value = mock_tab

    main_window.load_request_from_collection(Mock())

    mock_tab.load_request_data.assert_called_once()