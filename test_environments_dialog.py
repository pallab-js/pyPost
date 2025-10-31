import pytest
from unittest.mock import Mock, patch
from environments_dialog import EnvironmentsDialog


@pytest.fixture
def db_manager_mock():
    return Mock()


@pytest.fixture
def env_dialog(db_manager_mock):
    with patch('environments_dialog.DatabaseManager', return_value=db_manager_mock):
        dialog = EnvironmentsDialog(db_manager_mock)
        yield dialog


def test_environments_dialog_init(env_dialog, db_manager_mock):
    """Test EnvironmentsDialog initialization"""
    assert env_dialog.db_manager == db_manager_mock
    assert hasattr(env_dialog, 'env_combo')
    assert hasattr(env_dialog, 'variables_table')


def test_load_environments(env_dialog, db_manager_mock):
    """Test loading environments"""
    db_manager_mock.execute_query.return_value = [
        {"id": 1, "name": "Default"},
        {"id": 2, "name": "Production"}
    ]

    env_dialog.load_environments()

    assert env_dialog.env_combo.count() == 2
    assert env_dialog.env_combo.itemText(0) == "Default"


def test_load_variables(env_dialog, db_manager_mock):
    """Test loading variables for environment"""
    env_dialog.env_combo.currentData.return_value = 1
    db_manager_mock.execute_query.return_value = [
        {"id": 1, "name": "API_KEY", "value": "secret"},
        {"id": 2, "name": "BASE_URL", "value": "https://api.example.com"}
    ]

    env_dialog.load_variables()

    # Should set row count and items
    env_dialog.variables_table.setRowCount.assert_called_with(2)


@patch('environments_dialog.QInputDialog')
def test_add_environment(mock_input, env_dialog, db_manager_mock):
    """Test adding new environment"""
    mock_input.getText.return_value = ("NewEnv", True)
    db_manager_mock.execute_update.return_value = 1

    env_dialog.add_environment()

    db_manager_mock.execute_update.assert_called_once_with("INSERT INTO environments (name) VALUES (?)", ("NewEnv",))
    env_dialog.load_environments.assert_called_once()


@patch('environments_dialog.QInputDialog')
def test_add_environment_duplicate(mock_input, env_dialog, db_manager_mock):
    """Test adding duplicate environment"""
    mock_input.getText.return_value = ("Default", True)
    db_manager_mock.execute_update.side_effect = Exception("UNIQUE constraint failed")

    with patch('environments_dialog.QMessageBox') as mock_msgbox:
        env_dialog.add_environment()

    mock_msgbox.warning.assert_called_once()


@patch('environments_dialog.QMessageBox')
def test_delete_environment(mock_msgbox, env_dialog, db_manager_mock):
    """Test deleting environment"""
    env_dialog.env_combo.currentData.return_value = 1
    env_dialog.env_combo.currentText.return_value = "TestEnv"
    mock_msgbox.question.return_value = 16384  # Yes

    env_dialog.delete_environment()

    db_manager_mock.execute_update.assert_called_once_with("DELETE FROM environments WHERE id = ?", (1,))
    env_dialog.load_environments.assert_called_once()


@patch('environments_dialog.QMessageBox')
def test_delete_environment_cancel(mock_msgbox, env_dialog, db_manager_mock):
    """Test canceling environment deletion"""
    env_dialog.env_combo.currentData.return_value = 1
    mock_msgbox.question.return_value = 65536  # No

    env_dialog.delete_environment()

    db_manager_mock.execute_update.assert_not_called()


@patch('environments_dialog.QInputDialog')
def test_add_variable(mock_input, env_dialog, db_manager_mock):
    """Test adding variable to environment"""
    env_dialog.env_combo.currentData.return_value = 1
    mock_input.getText.side_effect = [("API_KEY", True), ("secret", True)]
    db_manager_mock.execute_update.return_value = 1

    env_dialog.add_variable()

    db_manager_mock.execute_update.assert_called_once_with(
        "INSERT INTO environment_variables (environment_id, name, value) VALUES (?, ?, ?)",
        (1, "API_KEY", "secret")
    )
    env_dialog.load_variables.assert_called_once()


@patch('environments_dialog.QMessageBox')
def test_add_variable_no_env(mock_msgbox, env_dialog):
    """Test adding variable without selecting environment"""
    env_dialog.env_combo.currentData.return_value = None

    env_dialog.add_variable()

    mock_msgbox.warning.assert_called_once()


@patch('environments_dialog.QMessageBox')
def test_delete_variable(mock_msgbox, env_dialog, db_manager_mock):
    """Test deleting variable"""
    env_dialog.env_combo.currentData.return_value = 1
    env_dialog.variables_table.currentRow.return_value = 0

    mock_item = Mock()
    mock_item.text.return_value = "API_KEY"
    env_dialog.variables_table.item.return_value = mock_item

    mock_msgbox.question.return_value = 16384  # Yes

    env_dialog.delete_variable()

    db_manager_mock.execute_update.assert_called_once_with(
        "DELETE FROM environment_variables WHERE environment_id = ? AND name = ?",
        (1, "API_KEY")
    )
    env_dialog.load_variables.assert_called_once()


def test_delete_variable_no_selection(mock_msgbox, env_dialog):
    """Test deleting variable without selection"""
    env_dialog.variables_table.currentRow.return_value = -1

    env_dialog.delete_variable()

    # Should not do anything
    env_dialog.variables_table.item.assert_not_called()