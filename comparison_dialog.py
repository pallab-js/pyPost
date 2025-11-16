from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QSplitter,
    QPushButton, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
import json
import difflib


class ComparisonDialog(QDialog):
    """Dialog for comparing two requests/responses"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compare Requests/Responses")
        self.setModal(True)
        self.resize(1000, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Selection controls
        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QLabel("Compare:"))
        self.compare_type = QComboBox()
        self.compare_type.addItems(["Requests", "Responses"])
        self.compare_type.currentTextChanged.connect(self.update_comparison)
        controls_layout.addWidget(self.compare_type)

        controls_layout.addStretch()

        self.compare_btn = QPushButton("Compare")
        self.compare_btn.clicked.connect(self.perform_comparison)
        controls_layout.addWidget(self.compare_btn)

        layout.addLayout(controls_layout)

        # Splitter for side-by-side comparison
        splitter = QSplitter(Qt.Horizontal)

        # Left side
        left_widget = self.create_comparison_panel("Left")
        splitter.addWidget(left_widget)

        # Right side
        right_widget = self.create_comparison_panel("Right")
        splitter.addWidget(right_widget)

        # Set splitter proportions
        splitter.setSizes([500, 500])

        layout.addWidget(splitter)

        # Diff view
        diff_group = QVBoxLayout()
        diff_group.addWidget(QLabel("Differences:"))
        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setFontFamily("Monospace")
        diff_group.addWidget(self.diff_view)

        layout.addLayout(diff_group)

        self.setLayout(layout)

    def create_comparison_panel(self, title: str):
        """Create a comparison panel"""
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox

        panel = QWidget()
        layout = QVBoxLayout()

        group = QGroupBox(f"{title} Request/Response")
        group_layout = QVBoxLayout()

        self.__dict__[f"{title.lower()}_text"] = QTextEdit()
        self.__dict__[f"{title.lower()}_text"].setPlaceholderText(f"Paste {title.lower()} content here...")
        group_layout.addWidget(self.__dict__[f"{title.lower()}_text"])

        group.setLayout(group_layout)
        layout.addWidget(group)

        panel.setLayout(layout)
        return panel

    def update_comparison(self, compare_type: str):
        """Update UI based on comparison type"""
        placeholder = "request" if compare_type == "Requests" else "response"
        self.left_text.setPlaceholderText(f"Paste left {placeholder} content here...")
        self.right_text.setPlaceholderText(f"Paste right {placeholder} content here...")

    def perform_comparison(self):
        """Perform the comparison and show differences"""
        left_content = self.left_text.toPlainText().strip()
        right_content = self.right_text.toPlainText().strip()

        if not left_content or not right_content:
            QMessageBox.warning(self, "Missing Content", "Please provide content for both sides")
            return

        try:
            # Try to parse as JSON for better comparison
            left_json = json.loads(left_content)
            right_json = json.loads(right_content)

            # Pretty print for comparison
            left_formatted = json.dumps(left_json, indent=2, sort_keys=True)
            right_formatted = json.dumps(right_json, indent=2, sort_keys=True)

            # Generate diff
            diff = self.generate_json_diff(left_formatted, right_formatted)

        except json.JSONDecodeError:
            # Fall back to text comparison
            diff = self.generate_text_diff(left_content, right_content)

        self.diff_view.setPlainText(diff)

    def generate_json_diff(self, left: str, right: str) -> str:
        """Generate a diff for JSON content"""
        left_lines = left.splitlines()
        right_lines = right.splitlines()

        diff = difflib.unified_diff(
            left_lines,
            right_lines,
            fromfile="Left",
            tofile="Right",
            lineterm=""
        )

        return "\n".join(diff)

    def generate_text_diff(self, left: str, right: str) -> str:
        """Generate a diff for plain text content"""
        left_lines = left.splitlines()
        right_lines = right.splitlines()

        diff = difflib.unified_diff(
            left_lines,
            right_lines,
            fromfile="Left",
            tofile="Right",
            lineterm=""
        )

        return "\n".join(diff)