import sqlite3
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QDialogButtonBox, QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt

from database import DatabaseManager


class EnvironmentsDialog(QDialog):
    """Dialog for managing environments and variables"""

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.init_ui()
        self.load_environments()

    def init_ui(self):
        self.setWindowTitle("Manage Environments")
        self.setModal(True)
        self.resize(600, 400)

        layout = QVBoxLayout()

        # Environment selection
        env_layout = QHBoxLayout()
        env_layout.addWidget(QLabel("Environment:"))
        self.env_combo = QComboBox()
        self.env_combo.currentTextChanged.connect(self.load_variables)
        env_layout.addWidget(self.env_combo)

        self.add_env_btn = QPushButton("Add Environment")
        self.add_env_btn.clicked.connect(self.add_environment)
        env_layout.addWidget(self.add_env_btn)

        self.delete_env_btn = QPushButton("Delete Environment")
        self.delete_env_btn.clicked.connect(self.delete_environment)
        env_layout.addWidget(self.delete_env_btn)

        layout.addLayout(env_layout)

        # Variables table
        self.variables_table = QTableWidget()
        self.variables_table.setColumnCount(2)
        self.variables_table.setHorizontalHeaderLabels(['Name', 'Value'])
        self.variables_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.variables_table)

        # Variable buttons
        var_btn_layout = QHBoxLayout()
        self.add_var_btn = QPushButton("Add Variable")
        self.add_var_btn.clicked.connect(self.add_variable)
        self.delete_var_btn = QPushButton("Delete Variable")
        self.delete_var_btn.clicked.connect(self.delete_variable)
        var_btn_layout.addWidget(self.add_var_btn)
        var_btn_layout.addWidget(self.delete_var_btn)
        var_btn_layout.addStretch()
        layout.addLayout(var_btn_layout)

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_environments(self):
        """Load environments from database"""
        environments = self.db_manager.execute_query("SELECT * FROM environments ORDER BY name")
        self.env_combo.clear()
        for env in environments:
            self.env_combo.addItem(env['name'], env['id'])

    def load_variables(self):
        """Load variables for selected environment"""
        env_id = self.env_combo.currentData()
        if not env_id:
            self.variables_table.setRowCount(0)
            return

        variables = self.db_manager.execute_query(
            "SELECT * FROM environment_variables WHERE environment_id = ? ORDER BY name",
            (env_id,)
        )

        self.variables_table.setRowCount(len(variables))
        for i, var in enumerate(variables):
            self.variables_table.setItem(i, 0, QTableWidgetItem(var['name']))
            self.variables_table.setItem(i, 1, QTableWidgetItem(var['value']))

    def add_environment(self):
        """Add new environment"""
        name, ok = QInputDialog.getText(self, "New Environment", "Environment name:")
        if ok and name.strip():
            try:
                self.db_manager.execute_update(
                    "INSERT INTO environments (name) VALUES (?)",
                    (name.strip(),)
                )
                self.load_environments()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Error", "Environment name already exists")

    def delete_environment(self):
        """Delete selected environment"""
        env_id = self.env_combo.currentData()
        if not env_id:
            return

        reply = QMessageBox.question(
            self, "Delete Environment",
            f"Are you sure you want to delete '{self.env_combo.currentText()}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.db_manager.execute_update("DELETE FROM environments WHERE id = ?", (env_id,))
            self.load_environments()

    def add_variable(self):
        """Add new variable to current environment"""
        env_id = self.env_combo.currentData()
        if not env_id:
            QMessageBox.warning(self, "Error", "Please select an environment first")
            return

        name, ok = QInputDialog.getText(self, "New Variable", "Variable name:")
        if ok and name.strip():
            value, ok = QInputDialog.getText(self, "New Variable", "Variable value:")
            if ok:
                self.db_manager.execute_update(
                    "INSERT INTO environment_variables (environment_id, name, value) VALUES (?, ?, ?)",
                    (env_id, name.strip(), value)
                )
                self.load_variables()

    def delete_variable(self):
        """Delete selected variable"""
        current_row = self.variables_table.currentRow()
        if current_row < 0:
            return

        name_item = self.variables_table.item(current_row, 0)
        if name_item:
            reply = QMessageBox.question(
                self, "Delete Variable",
                f"Are you sure you want to delete variable '{name_item.text()}'?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                env_id = self.env_combo.currentData()
                self.db_manager.execute_update(
                    "DELETE FROM environment_variables WHERE environment_id = ? AND name = ?",
                    (env_id, name_item.text())
                )
                self.load_variables()