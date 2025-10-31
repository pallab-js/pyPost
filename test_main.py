import pytest
from unittest.mock import Mock, patch
import main


@patch('main.QApplication')
@patch('main.MainWindow')
def test_main_function(mock_main_window, mock_app):
    """Test main function"""
    mock_app_instance = Mock()
    mock_app.return_value = mock_app_instance
    mock_app_instance.exec.return_value = 0

    mock_window_instance = Mock()
    mock_main_window.return_value = mock_window_instance

    with patch('main.sys') as mock_sys:
        mock_sys.exit = Mock()
        main.main()

    mock_app.assert_called_once()
    mock_app_instance.setApplicationName.assert_called_once_with("pyPost")
    mock_app_instance.setApplicationVersion.assert_called_once_with("1.0.0")
    mock_app_instance.setStyle.assert_called_once_with('Fusion')
    mock_main_window.assert_called_once()
    mock_window_instance.show.assert_called_once()
    mock_app_instance.exec.assert_called_once()
    mock_sys.exit.assert_called_once_with(0)


@patch('main.logging')
def test_main_logging_setup(mock_logging):
    """Test that logging is configured in main"""
    with patch('main.QApplication'), patch('main.MainWindow'), patch('main.sys'):
        main.main()

    mock_logging.basicConfig.assert_called_once()
    args = mock_logging.basicConfig.call_args
    assert args[1]['level'] == mock_logging.INFO
    assert 'format' in args[1]