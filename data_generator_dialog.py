from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QComboBox, QSpinBox, QGroupBox, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from typing import Dict, Any
import json

from utils.data_generator import DataGenerator, TemplateEngine, DataType


class DataGeneratorDialog(QDialog):
    PLACEHOLDER_TYPES = [
        ("{{first_name}}", "First Name"),
        ("{{last_name}}", "Last Name"),
        ("{{full_name}}", "Full Name"),
        ("{{email}}", "Email"),
        ("{{username}}", "Username"),
        ("{{password(16)}}", "Password (16 chars)"),
        ("{{phone}}", "Phone"),
        ("{{address}}", "Address"),
        ("{{city}}", "City"),
        ("{{state}}", "State"),
        ("{{country}}", "Country"),
        ("{{zip}}", "ZIP Code"),
        ("{{company}}", "Company"),
        ("{{job_title}}", "Job Title"),
        ("{{uuid}}", "UUID"),
        ("{{integer}}", "Integer"),
        ("{{float}}", "Float"),
        ("{{boolean}}", "Boolean"),
        ("{{date}}", "Date"),
        ("{{datetime}}", "DateTime"),
        ("{{url}}", "URL"),
        ("{{ip}}", "IP Address"),
        ("{{color}}", "Color"),
        ("{{hex_color}}", "Hex Color"),
        ("{{word}}", "Word"),
        ("{{sentence}}", "Sentence"),
        ("{{paragraph}}", "Paragraph"),
        ("{{text(50)}}", "Text (50 chars)"),
        ("{{number_between(1, 100)}}", "Number (1-100)"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.generator = DataGenerator()
        self.template_engine = TemplateEngine(self.generator)
        self.template = ""
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Test Data Generator")
        self.setGeometry(200, 200, 800, 600)

        layout = QVBoxLayout()

        header = QLabel("Generate Test Data")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        placeholders_group = QGroupBox("Available Placeholders")
        placeholders_layout = QHBoxLayout()

        self.placeholder_list = QListWidget()
        for placeholder, desc in self.PLACEHOLDER_TYPES:
            self.placeholder_list.addItem(f"{desc} - {placeholder}")
        self.placeholder_list.itemDoubleClicked.connect(self.insert_placeholder)
        placeholders_layout.addWidget(self.placeholder_list)

        placeholder_btn_layout = QVBoxLayout()
        insert_btn = QPushButton("Insert →")
        insert_btn.clicked.connect(self.insert_placeholder)
        placeholder_btn_layout.addWidget(insert_btn)
        placeholders_layout.addLayout(placeholder_btn_layout)

        placeholders_group.setLayout(placeholders_layout)
        layout.addWidget(placeholders_group)

        template_group = QGroupBox("Template (use {{placeholder}} syntax)")
        template_layout = QVBoxLayout()
        self.template_edit = QTextEdit()
        self.template_edit.setPlaceholderText(
            'Example: {"name": "{{full_name}}", "email": "{{email}}", "age": {{number_between(18, 65)}}}\n'
            'Or: {{first_name}} {{last_name}} - {{email}}'
        )
        template_edit_font = QFont("Courier New")
        self.template_edit.setFont(template_edit_font)
        template_layout.addWidget(self.template_edit)
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)

        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("Generate Count:"))
        self.count_spin = QSpinBox()
        self.count_spin.setMinimum(1)
        self.count_spin.setMaximum(1000)
        self.count_spin.setValue(1)
        options_layout.addWidget(self.count_spin)

        options_layout.addStretch()

        generate_btn = QPushButton("Generate")
        generate_btn.clicked.connect(self.generate_data)
        options_layout.addWidget(generate_btn)

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        options_layout.addWidget(copy_btn)

        layout.addLayout(options_layout)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_font = QFont("Courier New")
        self.output_text.setFont(output_font)
        layout.addWidget(QLabel("Generated Output:"))
        layout.addWidget(self.output_text)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def insert_placeholder(self, item=None):
        if item is None:
            item = self.placeholder_list.currentItem()
        if item:
            text = item.text()
            placeholder = text.split(" - ")[-1]
            cursor = self.template_edit.textCursor()
            cursor.insertText(placeholder)
            self.template_edit.setFocus()

    def generate_data(self):
        template = self.template_edit.toPlainText()
        if not template.strip():
            QMessageBox.warning(self, "Error", "Please enter a template")
            return

        count = self.count_spin.value()
        try:
            results = []
            for _ in range(count):
                result = self.template_engine.generate_from_template(template)
                results.append(result)

            if count == 1:
                self.output_text.setPlainText(results[0])
            else:
                self.output_text.setPlainText("\n---\n".join(results))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate data: {str(e)}")

    def copy_to_clipboard(self):
        text = self.output_text.toPlainText()
        if text:
            clipboard = self.clipboard()
            clipboard.setText(text)
            self.statusBar().showMessage("Copied to clipboard", 2000)
        else:
            QMessageBox.warning(self, "Warning", "No data to copy")
