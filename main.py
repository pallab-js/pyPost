#!/usr/bin/env python3
"""
pyPost - API testing tool
"""

import sys
import logging
import warnings
from PySide6.QtWidgets import QApplication

from main_window import MainWindow

# Suppress urllib3 SSL warning (harmless, just compatibility notice)
warnings.filterwarnings('ignore', message='.*urllib3.*OpenSSL.*')


def main():
    """Main application entry point"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    app = QApplication(sys.argv)
    app.setApplicationName("pyPost")
    app.setApplicationVersion("1.0.0")

    # Set application style
    app.setStyle('Fusion')

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()