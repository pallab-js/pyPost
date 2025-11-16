from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QInputDialog, QMessageBox, QTextEdit, QComboBox, QGroupBox
)
from PySide6.QtCore import Qt
import json


class TemplatesDialog(QDialog):
    """Dialog for managing request templates"""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Request Templates")
        self.setModal(True)
        self.resize(700, 500)
        self.init_ui()
        self.load_templates()

    def init_ui(self):
        layout = QVBoxLayout()

        # Templates list and controls
        list_layout = QHBoxLayout()

        # Templates list
        templates_group = QGroupBox("Templates")
        templates_layout = QVBoxLayout()

        self.templates_list = QListWidget()
        self.templates_list.itemDoubleClicked.connect(self.load_template)
        templates_layout.addWidget(self.templates_list)

        # Template buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.add_template)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.edit_template)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_template)
        btn_layout.addWidget(self.delete_btn)

        templates_layout.addLayout(btn_layout)
        templates_group.setLayout(templates_layout)
        list_layout.addWidget(templates_group)

        # Template details
        details_group = QGroupBox("Template Details")
        details_layout = QVBoxLayout()

        self.template_details = QTextEdit()
        self.template_details.setReadOnly(True)
        self.template_details.setPlaceholderText("Select a template to view details...")
        details_layout.addWidget(self.template_details)

        # Category filter
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        self.category_filter = QComboBox()
        self.category_filter.addItems(["All", "General", "Authentication", "REST API", "GraphQL", "WebSocket"])
        self.category_filter.currentTextChanged.connect(self.filter_templates)
        category_layout.addWidget(self.category_filter)
        category_layout.addStretch()
        details_layout.addLayout(category_layout)

        details_group.setLayout(details_layout)
        list_layout.addWidget(details_group)

        layout.addLayout(list_layout)

        # Dialog buttons
        buttons_layout = QHBoxLayout()
        self.load_btn = QPushButton("Load Template")
        self.load_btn.clicked.connect(self.load_selected_template)
        self.load_btn.setEnabled(False)
        buttons_layout.addWidget(self.load_btn)

        buttons_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(self.close_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

        # Connect signals
        self.templates_list.itemSelectionChanged.connect(self.update_details)

    def load_templates(self, category_filter="All"):
        """Load templates from database"""
        self.templates_list.clear()

        if category_filter == "All":
            templates = self.db_manager.execute_query("SELECT * FROM templates ORDER BY category, name")
        else:
            templates = self.db_manager.execute_query(
                "SELECT * FROM templates WHERE category = ? ORDER BY name",
                (category_filter,)
            )

        for template in templates:
            item = QListWidgetItem(f"{template['name']} ({template['category']})")
            item.setData(Qt.UserRole, template['id'])
            item.setData(Qt.UserRole + 1, template)
            self.templates_list.addItem(item)

    def filter_templates(self, category: str):
        """Filter templates by category"""
        self.load_templates(category)

    def update_details(self):
        """Update template details when selection changes"""
        current_item = self.templates_list.currentItem()
        if current_item:
            template = current_item.data(Qt.UserRole + 1)
            details = f"Name: {template['name']}\n"
            details += f"Category: {template['category']}\n"
            details += f"Description: {template.get('description', 'No description')}\n\n"
            details += "Template Data:\n"

            try:
                template_data = json.loads(template['template_data'])
                details += json.dumps(template_data, indent=2)
            except json.JSONDecodeError:
                details += template['template_data']

            self.template_details.setPlainText(details)
            self.load_btn.setEnabled(True)
        else:
            self.template_details.clear()
            self.load_btn.setEnabled(False)

    def add_template(self):
        """Add a new template"""
        name, ok = QInputDialog.getText(self, "New Template", "Template name:")
        if not ok or not name.strip():
            return

        # Get template data from current request tab
        main_window = self.parent()
        if hasattr(main_window, 'request_tabs'):
            current_tab = main_window.request_tabs.currentWidget()
            if hasattr(current_tab, 'get_request_data'):
                template_data = current_tab.get_request_data()
            else:
                QMessageBox.warning(self, "Error", "No request data available")
                return
        else:
            QMessageBox.warning(self, "Error", "Cannot access request data")
            return

        # Get description
        description, ok = QInputDialog.getText(self, "Template Description", "Description (optional):")
        if not ok:
            return

        # Get category
        category, ok = QInputDialog.getItem(
            self, "Template Category", "Category:",
            ["General", "Authentication", "REST API", "GraphQL", "WebSocket"], 0, False
        )
        if not ok:
            return

        try:
            self.db_manager.execute_update(
                "INSERT INTO templates (name, description, template_data, category) VALUES (?, ?, ?, ?)",
                (name.strip(), description.strip() if description else None,
                 json.dumps(template_data), category)
            )
            self.load_templates(self.category_filter.currentText())
            QMessageBox.information(self, "Success", "Template saved successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template: {str(e)}")

    def edit_template(self):
        """Edit selected template"""
        current_item = self.templates_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a template to edit")
            return

        template = current_item.data(Qt.UserRole + 1)

        # Edit name
        name, ok = QInputDialog.getText(self, "Edit Template", "Template name:",
                                       text=template['name'])
        if not ok or not name.strip():
            return

        # Edit description
        description, ok = QInputDialog.getText(self, "Edit Description", "Description:",
                                             text=template.get('description', ''))
        if not ok:
            return

        # Edit category
        categories = ["General", "Authentication", "REST API", "GraphQL", "WebSocket"]
        current_category_index = categories.index(template['category']) if template['category'] in categories else 0
        category, ok = QInputDialog.getItem(
            self, "Edit Category", "Category:", categories, current_category_index, False
        )
        if not ok:
            return

        try:
            self.db_manager.execute_update(
                "UPDATE templates SET name = ?, description = ?, category = ? WHERE id = ?",
                (name.strip(), description.strip() if description else None, category, template['id'])
            )
            self.load_templates(self.category_filter.currentText())
            QMessageBox.information(self, "Success", "Template updated successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update template: {str(e)}")

    def delete_template(self):
        """Delete selected template"""
        current_item = self.templates_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a template to delete")
            return

        template = current_item.data(Qt.UserRole + 1)

        reply = QMessageBox.question(
            self, "Delete Template",
            f"Are you sure you want to delete '{template['name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.db_manager.execute_update("DELETE FROM templates WHERE id = ?", (template['id'],))
                self.load_templates(self.category_filter.currentText())
                QMessageBox.information(self, "Success", "Template deleted successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete template: {str(e)}")

    def load_template(self, item: QListWidgetItem):
        """Load template when double-clicked"""
        self.load_selected_template()

    def load_selected_template(self):
        """Load selected template into current request tab"""
        current_item = self.templates_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a template to load")
            return

        template = current_item.data(Qt.UserRole + 1)

        try:
            template_data = json.loads(template['template_data'])

            # Load into current request tab
            main_window = self.parent()
            if hasattr(main_window, 'request_tabs'):
                current_tab = main_window.request_tabs.currentWidget()
                if hasattr(current_tab, 'load_request_data'):
                    current_tab.load_request_data(template_data)
                    QMessageBox.information(self, "Success", f"Template '{template['name']}' loaded successfully")
                    self.accept()  # Close dialog
                else:
                    QMessageBox.warning(self, "Error", "Cannot load template into current tab")
            else:
                QMessageBox.warning(self, "Error", "Cannot access request tabs")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load template: {str(e)}")