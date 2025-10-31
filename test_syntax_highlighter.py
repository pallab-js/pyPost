import pytest
from unittest.mock import Mock, patch
from syntax_highlighter import SyntaxHighlighter


@pytest.fixture
def highlighter():
    mock_parent = Mock()
    with patch('syntax_highlighter.PYGMENTS_AVAILABLE', True):
        hl = SyntaxHighlighter(mock_parent)
        yield hl


@pytest.fixture
def highlighter_no_pygments():
    mock_parent = Mock()
    with patch('syntax_highlighter.PYGMENTS_AVAILABLE', False):
        hl = SyntaxHighlighter(mock_parent)
        yield hl


def test_syntax_highlighter_init(highlighter):
    """Test SyntaxHighlighter initialization with Pygments"""
    assert highlighter.lexer is None
    assert hasattr(highlighter, 'formats')


def test_syntax_highlighter_init_no_pygments(highlighter_no_pygments):
    """Test SyntaxHighlighter initialization without Pygments"""
    assert highlighter_no_pygments.lexer is None
    assert highlighter_no_pygments.formats == {}


@patch('syntax_highlighter.JsonLexer')
def test_set_lexer_json(mock_json_lexer, highlighter):
    """Test setting JSON lexer"""
    highlighter.set_lexer('application/json')
    mock_json_lexer.assert_called_once()
    assert highlighter.lexer is not None


@patch('syntax_highlighter.XmlLexer')
def test_set_lexer_xml(mock_xml_lexer, highlighter):
    """Test setting XML lexer"""
    highlighter.set_lexer('application/xml')
    mock_xml_lexer.assert_called_once()
    assert highlighter.lexer is not None


def test_set_lexer_unknown(highlighter):
    """Test setting unknown content type"""
    highlighter.set_lexer('text/plain')
    assert highlighter.lexer is None


def test_set_lexer_no_pygments(highlighter_no_pygments):
    """Test setting lexer without Pygments"""
    highlighter_no_pygments.set_lexer('application/json')
    assert highlighter_no_pygments.lexer is None


@patch('syntax_highlighter.JsonLexer')
def test_highlight_block_json(mock_json_lexer, highlighter):
    """Test highlighting JSON block"""
    mock_lexer = Mock()
    mock_lexer.get_tokens.return_value = [
        ('Token.Keyword', 'null'),
        ('Token.Text', ' '),
        ('Token.String', '"key"')
    ]
    mock_json_lexer.return_value = mock_lexer

    highlighter.set_lexer('application/json')

    mock_document = Mock()
    highlighter.setDocument(mock_document)

    highlighter.highlightBlock('null "key"')

    # Should call setFormat for each token
    assert mock_document.setFormat.call_count > 0


def test_highlight_block_no_lexer(highlighter):
    """Test highlighting without lexer"""
    highlighter.lexer = None

    mock_document = Mock()
    highlighter.setDocument(mock_document)

    highlighter.highlightBlock('some text')

    # Should not call setFormat
    mock_document.setFormat.assert_not_called()


def test_highlight_block_no_pygments(highlighter_no_pygments):
    """Test highlighting without Pygments"""
    mock_document = Mock()
    highlighter_no_pygments.setDocument(mock_document)

    highlighter_no_pygments.highlightBlock('some text')

    mock_document.setFormat.assert_not_called()


@patch('syntax_highlighter.JsonLexer')
def test_highlight_block_exception(mock_json_lexer, highlighter):
    """Test highlighting with exception"""
    mock_lexer = Mock()
    mock_lexer.get_tokens.side_effect = Exception("Lexer error")
    mock_json_lexer.return_value = mock_lexer

    highlighter.set_lexer('application/json')

    mock_document = Mock()
    highlighter.setDocument(mock_document)

    # Should not raise exception
    highlighter.highlightBlock('invalid json')

    # Should still call setFormat if tokens were processed before exception
    # But in this case, exception happens immediately