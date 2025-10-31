from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor

try:
    from pygments import lex
    from pygments.lexers import JsonLexer, XmlLexer
    from pygments.token import Token
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


class SyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for response body using Pygments"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lexer = None
        self.formats = {}

        if PYGMENTS_AVAILABLE:
            # Define formats for token types
            self.formats[Token.Keyword] = QTextCharFormat()
            self.formats[Token.Keyword].setForeground(QColor("blue"))
            self.formats[Token.Keyword].setFontWeight(700)

            self.formats[Token.String] = QTextCharFormat()
            self.formats[Token.String].setForeground(QColor("green"))

            self.formats[Token.Number] = QTextCharFormat()
            self.formats[Token.Number].setForeground(QColor("orange"))

            self.formats[Token.Comment] = QTextCharFormat()
            self.formats[Token.Comment].setForeground(QColor("gray"))
            self.formats[Token.Comment].setFontItalic(True)

            self.formats[Token.Name] = QTextCharFormat()
            self.formats[Token.Name].setForeground(QColor("black"))

    def highlightBlock(self, text: str):
        if not PYGMENTS_AVAILABLE or not self.lexer:
            return

        try:
            tokens = self.lexer.get_tokens(text)
            start = 0
            for token_type, value in tokens:
                length = len(value)
                if token_type in self.formats:
                    self.setFormat(start, length, self.formats[token_type])
                start += length
        except Exception:
            pass

    def set_lexer(self, content_type: str):
        """Set the appropriate lexer based on content type"""
        if not PYGMENTS_AVAILABLE:
            return

        content_type = content_type.lower()
        if 'json' in content_type:
            self.lexer = JsonLexer()
        elif 'xml' in content_type:
            self.lexer = XmlLexer()
        else:
            self.lexer = None