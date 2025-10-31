import json
import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget,
    QTreeView, QListWidget, QComboBox, QPushButton, QLabel, QInputDialog,
    QMessageBox, QListWidgetItem, QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem, QShortcut, QKeySequence, QPalette, QColor

from database import DatabaseManager
from request_tab import RequestTab
from environments_dialog import EnvironmentsDialog


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle("pyPost - API Testing Tool")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout()

        # Create splitter for three-pane layout
        splitter = QSplitter(Qt.Horizontal)

        # Left sidebar
        self.sidebar = self.create_sidebar()
        splitter.addWidget(self.sidebar)

        # Main panel (center)
        self.main_panel = self.create_main_panel()
        splitter.addWidget(self.main_panel)

        # Set splitter proportions
        splitter.setSizes([300, 900])

        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)

        # Menu bar
        self.create_menu_bar()

        # Status bar
        self.statusBar().showMessage("Ready")

    def create_sidebar(self) -> QWidget:
        """Create left sidebar with collections and history"""
        sidebar = QWidget()
        layout = QVBoxLayout()

        # Sidebar tabs
        self.sidebar_tabs = QTabWidget()

        # Collections tab
        self.collections_tree = QTreeView()
        self.collections_model = QStandardItemModel()
        self.collections_tree.setModel(self.collections_model)
        self.collections_tree.setHeaderHidden(True)
        self.sidebar_tabs.addTab(self.collections_tree, "Collections")

        # History tab
        self.history_list = QListWidget()
        self.sidebar_tabs.addTab(self.history_list, "History")

        layout.addWidget(self.sidebar_tabs)
        sidebar.setLayout(layout)
        return sidebar

    def create_main_panel(self) -> QWidget:
        """Create main panel with request tabs"""
        main_panel = QWidget()
        layout = QVBoxLayout()

        # Environment selector in toolbar area
        env_layout = QHBoxLayout()
        env_layout.addWidget(QLabel("Environment:"))
        self.env_selector = QComboBox()
        self.env_selector.currentTextChanged.connect(self.on_environment_changed)
        env_layout.addWidget(self.env_selector)

        self.manage_env_btn = QPushButton("Manage Environments")
        self.manage_env_btn.clicked.connect(self.manage_environments)
        env_layout.addWidget(self.manage_env_btn)
        env_layout.addStretch()

        layout.addLayout(env_layout)

        # Request tabs
        self.request_tabs = QTabWidget()
        self.request_tabs.setTabsClosable(True)
        self.request_tabs.tabCloseRequested.connect(self.close_request_tab)
        layout.addWidget(self.request_tabs)

        # Add initial tab
        self.add_request_tab()

        main_panel.setLayout(layout)
        return main_panel

    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        new_request_action = file_menu.addAction("New Request")
        new_request_action.setShortcut(QKeySequence("Ctrl+N"))
        new_request_action.triggered.connect(self.add_request_tab)

        save_request_action = file_menu.addAction("Save Request")
        save_request_action.setShortcut(QKeySequence("Ctrl+S"))
        save_request_action.triggered.connect(self.save_current_request)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        file_menu.addSeparator()

        import_action = file_menu.addAction("Import Collections")
        import_action.triggered.connect(self.import_collections)

        export_action = file_menu.addAction("Export Collections")
        export_action.triggered.connect(self.export_collections)

        # View menu
        view_menu = menubar.addMenu("View")

        self.dark_mode_action = view_menu.addAction("Dark Mode")
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)

        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)

    def load_data(self):
        """Load data from database"""
        self.load_environments()
        self.load_collections()
        self.load_history()
        self.load_settings()

    def load_environments(self):
        """Load environments into selector"""
        environments = self.db_manager.execute_query("SELECT * FROM environments ORDER BY name")
        self.env_selector.clear()
        for env in environments:
            self.env_selector.addItem(env['name'], env['id'])

    def load_collections(self):
        """Load collections into tree view"""
        collections = self.db_manager.execute_query(
            "SELECT * FROM collections ORDER BY parent_id, name"
        )

        self.collections_model.clear()
        self.collections_model.setHeaderData(0, Qt.Horizontal, "Collections")

        # Build tree structure
        items = {}
        for collection in collections:
            item = QStandardItem(collection['name'])
            item.setData(collection['id'], Qt.UserRole)
            item.setData(collection, Qt.UserRole + 1)  # Store full collection data
            items[collection['id']] = item

        for collection in collections:
            if collection['parent_id'] is None:
                self.collections_model.appendRow(items[collection['id']])
            else:
                parent_item = items.get(collection['parent_id'])
                if parent_item:
                    parent_item.appendRow(items[collection['id']])

        # Connect double-click to load request
        self.collections_tree.doubleClicked.connect(self.load_request_from_collection)

    def load_history(self):
        """Load history into list widget"""
        history = self.db_manager.execute_query(
            "SELECT * FROM history ORDER BY created_at DESC LIMIT 100"
        )

        self.history_list.clear()
        for entry in history:
            status_code = entry.get('status_code', '-')
            created_at = entry.get('created_at', '')
            # Truncate URL if too long for display
            url_display = entry['url']
            if len(url_display) > 50:
                url_display = url_display[:47] + "..."
            item_text = f"{entry['method']} {url_display} - {status_code} ({created_at})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, entry['id'])
            item.setData(Qt.UserRole + 1, entry)  # Store full entry data
            self.history_list.addItem(item)
        
        # Connect double-click to load request
        self.history_list.doubleClicked.connect(self.load_request_from_history)

    def add_request_tab(self):
        """Add new request tab"""
        tab = RequestTab(self.db_manager)
        tab_name = f"Request {self.request_tabs.count() + 1}"
        self.request_tabs.addTab(tab, tab_name)
        self.request_tabs.setCurrentWidget(tab)

    def close_request_tab(self, index: int):
        """Close request tab at given index"""
        if self.request_tabs.count() > 1:
            self.request_tabs.removeTab(index)
        else:
            QMessageBox.information(self, "Info", "At least one request tab must remain open")

    def manage_environments(self):
        """Open environments management dialog"""
        dialog = EnvironmentsDialog(self.db_manager, self)
        if dialog.exec() == QDialog.Accepted:
            self.load_environments()

    def on_environment_changed(self, environment_name: str):
        """Handle environment selection change"""
        # Update all request tabs with new environment
        for i in range(self.request_tabs.count()):
            tab = self.request_tabs.widget(i)
            if isinstance(tab, RequestTab):
                tab.current_environment = environment_name
                tab.substitute_variables()

    def load_request_from_collection(self, index):
        """Load request from collection into current tab"""
        item = self.collections_model.itemFromIndex(index)
        if not item:
            return

        collection_data = item.data(Qt.UserRole + 1)
        if not collection_data or not collection_data.get('request_data'):
            return

        # Get current tab or create new one
        current_tab = self.request_tabs.currentWidget()
        if not isinstance(current_tab, RequestTab):
            self.add_request_tab()
            current_tab = self.request_tabs.currentWidget()

        # Load request data
        request_data = json.loads(collection_data['request_data'])
        current_tab.load_request_data(request_data)

    def save_current_request(self):
        """Save current request to collections"""
        current_tab = self.request_tabs.currentWidget()
        if not isinstance(current_tab, RequestTab):
            return

        # Get request data
        request_data = current_tab.get_request_data()
        if not request_data.get('url'):
            QMessageBox.warning(self, "Error", "Please enter a URL to save")
            return

        # Show save dialog
        name, ok = QInputDialog.getText(self, "Save Request", "Request name:")
        if ok and name.strip():
            try:
                self.db_manager.execute_update(
                    "INSERT INTO collections (name, request_data, is_folder) VALUES (?, ?, 0)",
                    (name.strip(), json.dumps(request_data))
                )
                self.load_collections()
                QMessageBox.information(self, "Success", "Request saved successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save request: {str(e)}")

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About pyPost",
            "pyPost - API testing tool\n\n"
            "Version 1.0.0"
        )

    def import_collections(self):
        """Import collections from JSON file"""
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Collections", "", "JSON Files (*.json)")
        if not file_path:
            return

        import json
        try:
            with open(file_path, 'r') as f:
                collections = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
            return

        imported = 0
        for coll in collections:
            try:
                self.db_manager.execute_update(
                    "INSERT INTO collections (name, parent_id, is_folder, request_data) VALUES (?, ?, ?, ?)",
                    (coll['name'], coll.get('parent_id'), coll.get('is_folder', 0), coll.get('request_data'))
                )
                imported += 1
            except Exception as e:
                QMessageBox.warning(self, "Import Error", f"Failed to import {coll['name']}: {str(e)}")

        if imported > 0:
            self.load_collections()
            QMessageBox.information(self, "Success", f"Imported {imported} collections successfully")

    def export_collections(self):
        """Export collections to JSON file"""
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Collections", "", "JSON Files (*.json)")
        if not file_path:
            return

        collections = self.db_manager.execute_query("SELECT * FROM collections")
        import json
        try:
            with open(file_path, 'w') as f:
                json.dump(collections, f, indent=2)
            QMessageBox.information(self, "Success", "Collections exported successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")

    def toggle_dark_mode(self):
        """Toggle between light and dark mode"""
        if self.dark_mode_action.isChecked():
            self.set_dark_palette()
            self.save_dark_mode_preference(True)
        else:
            self.set_light_palette()
            self.save_dark_mode_preference(False)
    
    def save_dark_mode_preference(self, enabled: bool):
        """Save dark mode preference to database"""
        try:
            self.db_manager.execute_update(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ('dark_mode', '1' if enabled else '0')
            )
        except Exception as e:
            logging.warning(f"Failed to save dark mode preference: {e}")
    
    def load_settings(self):
        """Load application settings from database"""
        try:
            # Load dark mode preference
            result = self.db_manager.execute_query(
                "SELECT value FROM settings WHERE key = ?",
                ('dark_mode',)
            )
            if result and result[0]['value'] == '1':
                self.dark_mode_action.setChecked(True)
                self.set_dark_palette()
        except Exception as e:
            logging.warning(f"Failed to load settings: {e}")

    def set_dark_palette(self):
        """Apply dark palette"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)

    def set_light_palette(self):
        """Apply light palette (default)"""
        self.setPalette(self.style().standardPalette())
    
    def load_request_from_history(self, item: QListWidgetItem):
        """Load request from history entry"""
        history_id = item.data(Qt.UserRole)
        if not history_id:
            return
        
        # Get history entry (we can use stored data or query)
        entry = item.data(Qt.UserRole + 1)
        if not entry:
            # Fallback to query if data not stored
            history = self.db_manager.execute_query(
                "SELECT * FROM history WHERE id = ?",
                (history_id,)
            )
            if not history:
                return
            entry = history[0]
        
        # Parse request data
        try:
            request_data_str = entry.get('request_data')
            if not request_data_str:
                QMessageBox.warning(self, "Error", "No request data found in history entry")
                return
            
            request_data = json.loads(request_data_str)
        except (json.JSONDecodeError, TypeError) as e:
            QMessageBox.warning(self, "Error", f"Failed to parse request data: {str(e)}")
            return
        
        # Get current tab or create new one
        current_tab = self.request_tabs.currentWidget()
        if not isinstance(current_tab, RequestTab):
            self.add_request_tab()
            current_tab = self.request_tabs.currentWidget()
        
        # Load request data
        if isinstance(current_tab, RequestTab):
            try:
                current_tab.load_request_data(request_data)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load request data: {str(e)}")
                return
            
            # Optionally show response if available
            response_data_str = entry.get('response_data')
            if response_data_str:
                try:
                    response_data = json.loads(response_data_str)
                    # Update tab name to show it's from history
                    tab_index = self.request_tabs.indexOf(current_tab)
                    if tab_index >= 0:
                        url = entry.get('url', '')
                        url_short = url[:30] + "..." if len(url) > 30 else url
                        method = entry.get('method', 'GET')
                        self.request_tabs.setTabText(tab_index, f"History: {method} {url_short}")
                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    logging.warning(f"Could not load response data from history: {e}")
                    pass  # Ignore if response data is invalid